"""OrgTree CLI: `uiao orgtree ...` subcommands.

Thin verbs over the loader/validator classes in
:mod:`uiao.modernization.orgtree`. Each validate verb wraps a single
`load_*` function: load defaults out of the ``uiao.canon.data.orgpath``
package or from an explicit ``--data PATH`` override, raise the
module's own typed validation error on bad input, print a one-line
summary on success.

The corpus this exercises is documented in canon UIAO_150-UIAO_176.
The PowerShell companion module under tools/powershell/OrgTreeValidation
calls these verbs for Functions 1-4 of UIAO_159; the PowerShell-native
collection helpers (Functions 5-6) wrap Microsoft Graph directly and
do not round-trip through this CLI.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable, Optional

import typer
from rich.console import Console

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
