"""OrgTree CLI: `uiao orgtree ...` subcommands.

Thin verbs over the loader/validator classes in
:mod:`uiao.modernization.orgtree`. Three verb groups:

- ``validate`` — schema + integrity check, one verb per corpus artifact
  plus an aggregate. Wraps the typed ``*ValidationError`` exceptions.
- ``show`` — read one entry from any of the canonical artifacts and
  pretty-print it. No tenant access.
- ``resolve`` — cross-reference one dynamic group's membership rule
  against the codebook (UIAO_151) and report referenced OrgPath
  validity.
- ``export`` — serialize a canonical artifact to JSON for downstream
  consumers (notably the PowerShell module's
  ``Get-OrgTreeValidationReport -CodebookPath``, UIAO_159 §F3).

The corpus this exercises is documented in canon UIAO_150-UIAO_176.
"""

from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path
from typing import Any, Callable, Optional

import typer
from rich.console import Console
from rich.table import Table

from uiao.modernization.orgtree.admin_units import (
    DelegationMatrix,
    DelegationMatrixValidationError,
    load_delegation_matrix,
)
from uiao.modernization.orgtree.codebook import (
    Codebook,
    CodebookValidationError,
    load_codebook,
)
from uiao.modernization.orgtree.device_planes import (
    DevicePlaneRegistry,
    DevicePlaneValidationError,
    load_device_plane_registry,
)
from uiao.modernization.orgtree.drift_engine_config import (
    DriftEngineConfig,
    DriftEngineConfigValidationError,
    load_drift_engine_config,
)
from uiao.modernization.orgtree.dynamic_groups import (
    DynamicGroupLibrary,
    DynamicGroupValidationError,
    load_dynamic_group_library,
)
from uiao.modernization.orgtree.policy_targets import (
    PolicyTargetingCanon,
    PolicyTargetingValidationError,
    load_policy_targeting_canon,
)

orgtree_app = typer.Typer(
    name="orgtree",
    help=(
        "OrgTree corpus operations (validate codebook / dynamic groups / "
        "admin units / device planes / policy targets / drift-engine "
        "config). Canon: UIAO_150-UIAO_176."
    ),
    no_args_is_help=True,
)

validate_app = typer.Typer(
    name="validate",
    help="Validate an OrgTree corpus file against its schema and integrity rules.",
    no_args_is_help=True,
)
orgtree_app.add_typer(validate_app, name="validate")

show_app = typer.Typer(
    name="show",
    help="Print one entry from a canonical OrgTree artifact.",
    no_args_is_help=True,
)
orgtree_app.add_typer(show_app, name="show")

resolve_app = typer.Typer(
    name="resolve",
    help="Cross-reference a corpus entry against the codebook and related artifacts.",
    no_args_is_help=True,
)
orgtree_app.add_typer(resolve_app, name="resolve")

export_app = typer.Typer(
    name="export",
    help="Serialize a canonical OrgTree artifact to a downstream-consumable format.",
    no_args_is_help=True,
)
orgtree_app.add_typer(export_app, name="export")

console = Console()


_DATA_OPT = typer.Option(
    None,
    "--data",
    "-d",
    help="Path to an alternate YAML file. Defaults to the canonical artifact under uiao.canon.data.orgpath.",
)


def _summarize_codebook(c: Codebook) -> str:
    return f"{len(c.entries)} entries, {len(c.deprecated)} deprecated, max_depth={c.max_depth}"


def _summarize_dynamic_groups(lib: DynamicGroupLibrary) -> str:
    return f"{len(lib.groups)} groups, {len(lib.purpose_suffixes)} purpose suffixes"


def _summarize_admin_units(m: DelegationMatrix) -> str:
    return (
        f"{len(m.administrative_units)} AUs, {len(m.roles)} role templates, "
        f"{len(m.admin_groups)} admin groups, {len(m.role_assignments)} assignments"
    )


def _summarize_device_planes(r: DevicePlaneRegistry) -> str:
    return f"{len(r.planes)} device planes, {len(r.skip_dispositions)} skip dispositions"


def _summarize_policy_targets(c: PolicyTargetingCanon) -> str:
    return f"{len(c.intune_assignments)} Intune assignments, {len(c.arc_policy_assignments)} Arc policy assignments"


def _summarize_drift_engine_config(c: DriftEngineConfig) -> str:
    return f"{len(c.phases)} phases, halt_at={c.severity_policy.halt_at}"


def _run(
    label: str,
    canon_id: str,
    loader: Callable[..., object],
    summarizer: Callable[[object], str],
    error_type: type[Exception],
    data: Optional[Path],
) -> bool:
    """Run one validate verb. Returns True on PASS, False on FAIL."""
    try:
        artifact = loader(path=data) if data is not None else loader()
    except error_type as exc:
        console.print(f"[red]FAIL[/red] {label} ({canon_id}): {exc}")
        return False
    summary = summarizer(artifact)
    console.print(f"[green]PASS[/green] {label} ({canon_id}) — {summary}")
    return True


@validate_app.command("codebook")
def validate_codebook(data: Optional[Path] = _DATA_OPT) -> None:
    """Validate the OrgPath codebook (UIAO_151)."""
    if not _run(
        "codebook",
        "UIAO_151",
        load_codebook,
        _summarize_codebook,  # type: ignore[arg-type]
        CodebookValidationError,
        data,
    ):
        raise typer.Exit(code=1)


@validate_app.command("dynamic-groups")
def validate_dynamic_groups(data: Optional[Path] = _DATA_OPT) -> None:
    """Validate the dynamic-group library (UIAO_152)."""
    if not _run(
        "dynamic-groups",
        "UIAO_152",
        load_dynamic_group_library,
        _summarize_dynamic_groups,  # type: ignore[arg-type]
        DynamicGroupValidationError,
        data,
    ):
        raise typer.Exit(code=1)


@validate_app.command("admin-units")
def validate_admin_units(data: Optional[Path] = _DATA_OPT) -> None:
    """Validate the delegation matrix — administrative units + roles (UIAO_154)."""
    if not _run(
        "admin-units",
        "UIAO_154",
        load_delegation_matrix,
        _summarize_admin_units,  # type: ignore[arg-type]
        DelegationMatrixValidationError,
        data,
    ):
        raise typer.Exit(code=1)


@validate_app.command("device-planes")
def validate_device_planes(data: Optional[Path] = _DATA_OPT) -> None:
    """Validate the device-plane registry (UIAO_153 / UIAO_171)."""
    if not _run(
        "device-planes",
        "UIAO_153",
        load_device_plane_registry,
        _summarize_device_planes,  # type: ignore[arg-type]
        DevicePlaneValidationError,
        data,
    ):
        raise typer.Exit(code=1)


@validate_app.command("policy-targets")
def validate_policy_targets(data: Optional[Path] = _DATA_OPT) -> None:
    """Validate the policy-targeting canon (UIAO_164)."""
    if not _run(
        "policy-targets",
        "UIAO_164",
        load_policy_targeting_canon,
        _summarize_policy_targets,  # type: ignore[arg-type]
        PolicyTargetingValidationError,
        data,
    ):
        raise typer.Exit(code=1)


@validate_app.command("drift-engine-config")
def validate_drift_engine_config(data: Optional[Path] = _DATA_OPT) -> None:
    """Validate the OrgTree drift-engine configuration (UIAO_163)."""
    if not _run(
        "drift-engine-config",
        "UIAO_163",
        load_drift_engine_config,
        _summarize_drift_engine_config,  # type: ignore[arg-type]
        DriftEngineConfigValidationError,
        data,
    ):
        raise typer.Exit(code=1)


@validate_app.command("all")
def validate_all() -> None:
    """Validate the full OrgTree corpus, in dependency order.

    Codebook (UIAO_151) -> dynamic groups (UIAO_152) -> admin units (UIAO_154)
    -> device planes (UIAO_153) -> policy targets (UIAO_164)
    -> drift-engine config (UIAO_163). Aggregates pass/fail; exits 1 if any
    individual artifact fails.
    """
    checks: list[tuple[str, str, Callable[..., object], Callable[[object], str], type[Exception]]] = [
        ("codebook", "UIAO_151", load_codebook, _summarize_codebook, CodebookValidationError),  # type: ignore[list-item]
        (
            "dynamic-groups",
            "UIAO_152",
            load_dynamic_group_library,
            _summarize_dynamic_groups,
            DynamicGroupValidationError,
        ),  # type: ignore[list-item]
        ("admin-units", "UIAO_154", load_delegation_matrix, _summarize_admin_units, DelegationMatrixValidationError),  # type: ignore[list-item]
        ("device-planes", "UIAO_153", load_device_plane_registry, _summarize_device_planes, DevicePlaneValidationError),  # type: ignore[list-item]
        (
            "policy-targets",
            "UIAO_164",
            load_policy_targeting_canon,
            _summarize_policy_targets,
            PolicyTargetingValidationError,
        ),  # type: ignore[list-item]
        (
            "drift-engine-config",
            "UIAO_163",
            load_drift_engine_config,
            _summarize_drift_engine_config,
            DriftEngineConfigValidationError,
        ),  # type: ignore[list-item]
    ]
    failed = 0
    for label, canon_id, loader, summarizer, err in checks:
        if not _run(label, canon_id, loader, summarizer, err, None):
            failed += 1
    console.print()
    if failed:
        console.print(f"[red]FAIL[/red] — {failed} of {len(checks)} corpus artifact(s) failed validation.")
        raise typer.Exit(code=1)
    console.print(f"[green]PASS[/green] — all {len(checks)} OrgTree corpus artifacts validated.")


# ---------------------------------------------------------------------------
# show — print one entry from a canonical artifact
# ---------------------------------------------------------------------------


def _print_record(title: str, record: object) -> None:
    """Render a frozen dataclass as a two-column key/value table."""
    table = Table(title=title, show_header=True, header_style="bold")
    table.add_column("field", style="cyan")
    table.add_column("value")
    for f in dataclasses.fields(record):  # type: ignore[arg-type]
        value = getattr(record, f.name)
        if dataclasses.is_dataclass(value):
            rendered = ", ".join(f"{k}={v!r}" for k, v in dataclasses.asdict(value).items())
        elif isinstance(value, (list, tuple)):
            rendered = ", ".join(repr(v) for v in value) if value else "(none)"
        elif isinstance(value, dict):
            rendered = ", ".join(f"{k}={v!r}" for k, v in value.items()) if value else "(none)"
        elif value is None:
            rendered = "(none)"
        else:
            rendered = str(value)
        table.add_row(f.name, rendered)
    console.print(table)


def _not_found(kind: str, key: str, available: list[str], plural: Optional[str] = None) -> None:
    """Print a NOT FOUND line listing up to five known keys.

    `plural` overrides the default kind pluralization for the trailing
    "Known {plural}:" hint (avoids "entrys" / "matrixs" rendering).
    """
    label = plural or f"{kind}s"
    sample = ", ".join(available[:5]) + (", …" if len(available) > 5 else "")
    console.print(f"[red]NOT FOUND[/red] {kind} '{key}'. Known {label}: {sample}")


@show_app.command("codebook")
def show_codebook_entry(code: str = typer.Argument(..., help="OrgPath code, e.g. ORG-FIN.")) -> None:
    """Print one codebook entry (UIAO_151)."""
    cb = load_codebook()
    entry = cb.entries.get(code)
    if entry is None:
        _not_found("codebook entry", code, sorted(cb.entries.keys()), plural="codebook entries")
        raise typer.Exit(code=1)
    _print_record(f"codebook entry — {code} (UIAO_151)", entry)


@show_app.command("dynamic-group")
def show_dynamic_group(name: str = typer.Argument(..., help="Group name, e.g. OrgTree-FIN-Users.")) -> None:
    """Print one dynamic group spec (UIAO_152)."""
    lib = load_dynamic_group_library()
    spec = lib.groups.get(name)
    if spec is None:
        _not_found("dynamic group", name, sorted(lib.groups.keys()))
        raise typer.Exit(code=1)
    _print_record(f"dynamic group — {name} (UIAO_152)", spec)


@show_app.command("admin-unit")
def show_admin_unit(name: str = typer.Argument(..., help="Administrative Unit name.")) -> None:
    """Print one Administrative Unit (UIAO_154)."""
    matrix = load_delegation_matrix()
    au = matrix.administrative_units.get(name)
    if au is None:
        _not_found("administrative unit", name, sorted(matrix.administrative_units.keys()))
        raise typer.Exit(code=1)
    _print_record(f"administrative unit — {name} (UIAO_154)", au)


@show_app.command("device-plane")
def show_device_plane(name: str = typer.Argument(..., help="Device-plane name.")) -> None:
    """Print one device plane (UIAO_153)."""
    reg = load_device_plane_registry()
    plane = reg.planes.get(name)
    if plane is None:
        _not_found("device plane", name, sorted(reg.planes.keys()))
        raise typer.Exit(code=1)
    _print_record(f"device plane — {name} (UIAO_153)", plane)


# ---------------------------------------------------------------------------
# resolve — cross-reference dynamic group rules against the codebook
# ---------------------------------------------------------------------------


@resolve_app.command("dynamic-group")
def resolve_dynamic_group(name: str = typer.Argument(..., help="Group name, e.g. OrgTree-FIN-Users.")) -> None:
    """Resolve a dynamic group's membership rule against the codebook (UIAO_151).

    Loads the group spec (UIAO_152) and the codebook (UIAO_151), prints
    the rule verbatim, and reports each OrgPath the rule references plus
    whether that code is registered. Exits 1 if any reference is
    unregistered (consistent with the dynamic-group integrity check).
    """
    lib = load_dynamic_group_library()
    spec = lib.groups.get(name)
    if spec is None:
        _not_found("dynamic group", name, sorted(lib.groups.keys()))
        raise typer.Exit(code=1)

    codebook = load_codebook()
    console.print(f"[bold]dynamic group:[/bold] {spec.name}  ([cyan]UIAO_152[/cyan])")
    console.print(f"  category: {spec.category}")
    console.print(f"  description: {spec.description}")
    console.print(f"  rule: [yellow]{spec.rule}[/yellow]")
    console.print()

    table = Table(title="OrgPath references", show_header=True, header_style="bold")
    table.add_column("orgpath")
    table.add_column("status")
    table.add_column("codebook description")
    missing = 0
    for ref in spec.orgpath_refs:
        entry = codebook.entries.get(ref)
        if entry is None:
            table.add_row(ref, "[red]MISSING[/red]", "(not in codebook)")
            missing += 1
        else:
            table.add_row(ref, "[green]OK[/green]", entry.description)
    console.print(table)

    if missing:
        console.print(f"[red]FAIL[/red] — {missing} reference(s) missing from codebook.")
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# export — emit canon as downstream-consumable JSON
# ---------------------------------------------------------------------------


def _codebook_to_payload(cb: Codebook) -> dict[str, Any]:
    """JSON-serializable shape consumed by UIAO_159's pwsh
    ``Get-OrgTreeValidationReport -CodebookPath``: an object with
    ``entries`` as a list of ``{code, level, description, parent}``.
    """
    return {
        "schema_version": cb.schema_version,
        "document_id": cb.document_id,
        "regex": cb.regex,
        "max_depth": cb.max_depth,
        "entries": [dataclasses.asdict(e) for e in cb.entries.values()],
        "deprecated": [dataclasses.asdict(e) for e in cb.deprecated.values()]
        if isinstance(cb.deprecated, dict)
        else [dataclasses.asdict(e) for e in cb.deprecated],
    }


@export_app.command("codebook")
def export_codebook(
    out: Optional[Path] = typer.Option(
        None,
        "--out",
        "-o",
        help="Destination JSON file. Defaults to stdout.",
    ),
) -> None:
    """Export the canonical codebook (UIAO_151) as JSON.

    The shape matches what ``Get-OrgTreeValidationReport -CodebookPath``
    consumes in the PowerShell companion module (UIAO_159 §F3): an
    object with an ``entries`` array, each entry exposing
    ``code/level/description/parent``.
    """
    cb = load_codebook()
    payload = _codebook_to_payload(cb)
    text = json.dumps(payload, indent=2, sort_keys=False)
    if out is None:
        sys.stdout.write(text)
        sys.stdout.write("\n")
    else:
        out.write_text(text + "\n", encoding="utf-8")
        console.print(f"[green]wrote[/green] {out} ({len(payload['entries'])} entries)")
