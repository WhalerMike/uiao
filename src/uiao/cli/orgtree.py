"""OrgTree CLI: ``uiao orgtree ...`` subcommands.

Thin verbs over the loader/validator classes in
:mod:`uiao.modernization.orgtree`.

Per ADR-078, the OrgTree corpus was reset to Model C (15-facet multi-
attribute). The speculative Model A consumer modules (admin-units,
device-planes, dynamic-groups, policy-targets, drift-engine-config)
and their CLI commands were retired in the same PR. The single
surviving command covers the Model C codebook:

- ``validate codebook`` — UIAO_151 OrgPath codebook (Model C)

Per-facet show/list/export commands and the broader corpus validators
will land alongside the rebuilt consumer modules in a follow-up
Phase 5 PR.

Canon: UIAO_151.
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from uiao.modernization.orgtree.codebook import (
    Codebook,
    CodebookValidationError,
    load_codebook,
)

orgtree_app = typer.Typer(
    name="orgtree",
    help=("OrgTree corpus operations (validate codebook). Canon: UIAO_151. Model C per ADR-078."),
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
