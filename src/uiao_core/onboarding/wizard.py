"""Interactive CLI wizard for creating a new canon YAML file.

Walks the user step-by-step through filling in every required field,
validates inputs in real-time with Pydantic, and writes a ready-to-use
``generation-inputs/<system_slug>.yaml`` file.

Usage::

    uiao init
    uiao setup-wizard
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import typer
import yaml
from pydantic import BaseModel, ConfigDict, ValidationError, field_validator
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

console = Console()

# ---------------------------------------------------------------------------
# Pydantic validation models (used for real-time input validation)
# ---------------------------------------------------------------------------

_FIPS_LEVELS = {"low", "moderate", "high"}
_DEPLOYMENT_MODELS = {"azure", "aws", "hybrid", "on_prem"}


class _SystemInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    system_name: str
    system_slug: str
    organization: str
    fips_categorization: str
    deployment_model: str

    @field_validator("system_slug")
    @classmethod
    def slug_format(cls, v: str) -> str:
        if not re.match(r"^[a-z0-9_]+$", v):
            raise ValueError("Slug must contain only lowercase letters, digits, and underscores.")
        return v

    @field_validator("fips_categorization")
    @classmethod
    def fips_valid(cls, v: str) -> str:
        if v.lower() not in _FIPS_LEVELS:
            raise ValueError(f"FIPS categorization must be one of: {', '.join(sorted(_FIPS_LEVELS))}")
        return v.lower()

    @field_validator("deployment_model")
    @classmethod
    def deployment_valid(cls, v: str) -> str:
        if v.lower() not in _DEPLOYMENT_MODELS:
            raise ValueError(f"Deployment model must be one of: {', '.join(sorted(_DEPLOYMENT_MODELS))}")
        return v.lower()


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def _prompt(label: str, default: str = "", hint: str = "") -> str:
    """Prompt for a non-empty value, retrying on blank input."""
    if hint:
        console.print(f"  [dim]{hint}[/dim]")
    while True:
        val = Prompt.ask(f"  [cyan]{label}[/cyan]", default=default).strip()
        if val:
            return val
        console.print("  [red]This field is required. Please enter a value.[/red]")


def _prompt_choice(label: str, choices: list[str], default: str = "") -> str:
    """Prompt for one of a fixed set of choices."""
    choices_str = " / ".join(f"[bold]{c}[/bold]" for c in choices)
    console.print(f"  Options: {choices_str}")
    while True:
        val = Prompt.ask(f"  [cyan]{label}[/cyan]", default=default).strip().lower()
        if val in choices:
            return val
        console.print(f"  [red]Invalid choice '[yellow]{val}[/yellow]'. Choose from: {', '.join(choices)}[/red]")


def _validate_field(model: type[BaseModel], field: str, value: Any) -> str | None:
    """Return an error message if *value* fails model validation for *field*, else None."""
    try:
        model.model_validate({field: value, **{k: "placeholder" for k in model.model_fields if k != field}})
    except ValidationError as exc:
        for error in exc.errors():
            if field in error.get("loc", ()):
                return str(error["msg"])
    return None


def _collect_components() -> list[dict[str, str]]:
    """Interactively collect key system components."""
    components: list[dict[str, str]] = []
    console.print("\n  [bold]Enter key system components[/bold] (press Enter with blank name to finish):")
    while True:
        name = Prompt.ask("    Component name (or blank to finish)", default="").strip()
        if not name:
            break
        role = Prompt.ask("    Role / description", default="").strip()
        components.append({"name": name, "role": role or name})
    return components


# ---------------------------------------------------------------------------
# Main wizard logic
# ---------------------------------------------------------------------------


def run_wizard(output_dir: Path = Path("generation-inputs")) -> Path:
    """Run the interactive onboarding wizard and write a canon YAML file.

    Parameters
    ----------
    output_dir:
        Directory where the generated canon YAML will be written.
        Defaults to ``generation-inputs/``.

    Returns
    -------
    Path
        The path of the generated canon YAML file.
    """
    console.print(
        Panel.fit(
            "[bold green]UIAO Canon Setup Wizard[/bold green]\n\n"
            "This wizard walks you through creating a new [bold]canon YAML[/bold] file.\n"
            "Answer each prompt; press [bold]Enter[/bold] to accept the default value shown in brackets.",
            title="uiao init",
        )
    )

    # ------------------------------------------------------------------
    # Step 1 — System identity
    # ------------------------------------------------------------------
    console.rule("[bold]Step 1 of 4 — System Identity[/bold]")

    system_name = _prompt(
        "System name",
        hint="Full name of the system or program (e.g. 'Agency Identity Platform')",
    )
    slug_default = re.sub(r"[^a-z0-9]+", "_", system_name.lower()).strip("_")
    system_slug = _prompt(
        "System slug",
        default=slug_default,
        hint="Short identifier used in filenames: lowercase letters, digits, underscores only",
    )
    # Validate slug format
    while not re.match(r"^[a-z0-9_]+$", system_slug):
        console.print("  [red]Slug must contain only lowercase letters, digits, and underscores.[/red]")
        system_slug = _prompt("System slug", default=slug_default)

    organization = _prompt(
        "Organization name",
        hint="Name of the owning agency / department (e.g. 'Department of Veterans Affairs')",
    )

    # ------------------------------------------------------------------
    # Step 2 — Compliance
    # ------------------------------------------------------------------
    console.rule("[bold]Step 2 of 4 — Compliance & Categorization[/bold]")

    fips_categorization = _prompt_choice(
        "FIPS 199 categorization",
        choices=["low", "moderate", "high"],
        default="moderate",
    )

    classification = _prompt(
        "Document classification",
        default="CUI//SP-CTI",
        hint="E.g. 'UNCLASSIFIED', 'CUI//SP-CTI', 'CUI/FOUO'",
    )

    audience_raw = _prompt(
        "Target audience (comma-separated roles)",
        default="CIO, CISO, PMO",
        hint="E.g. 'CIO, CISO, CTO, PMO'",
    )
    audience = [a.strip() for a in audience_raw.split(",") if a.strip()]

    # ------------------------------------------------------------------
    # Step 3 — Deployment model
    # ------------------------------------------------------------------
    console.rule("[bold]Step 3 of 4 — Deployment Model[/bold]")

    console.print(
        "  [dim]Choose the cloud service provider (CSP) or deployment model:\n"
        "  • [bold]azure[/bold]   — Microsoft Azure / Entra ID / Intune\n"
        "  • [bold]aws[/bold]     — AWS GovCloud\n"
        "  • [bold]hybrid[/bold]  — Multi-cloud (Azure + AWS)\n"
        "  • [bold]on_prem[/bold] — On-premises only[/dim]"
    )
    deployment_model = _prompt_choice(
        "Deployment model",
        choices=["azure", "aws", "hybrid", "on_prem"],
        default="azure",
    )

    # ------------------------------------------------------------------
    # Step 4 — Key components
    # ------------------------------------------------------------------
    console.rule("[bold]Step 4 of 4 — Key Components[/bold]")

    executive_summary = _prompt(
        "Executive summary (one sentence)",
        hint="Brief description of what this system does and why it exists",
    )

    program_overview = _prompt(
        "Program overview (one paragraph)",
        hint="More detailed description for the leadership briefing document",
    )

    components = _collect_components()

    # ------------------------------------------------------------------
    # Preview
    # ------------------------------------------------------------------
    console.rule("[bold]Review[/bold]")
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("System name", system_name)
    table.add_row("Slug", system_slug)
    table.add_row("Organization", organization)
    table.add_row("FIPS categorization", fips_categorization)
    table.add_row("Classification", classification)
    table.add_row("Deployment model", deployment_model)
    table.add_row("Audience", ", ".join(audience))
    table.add_row("Components", str(len(components)))
    console.print(table)

    if not Confirm.ask("\n  [bold]Write this canon file?[/bold]", default=True):
        console.print("[yellow]Wizard cancelled. No file written.[/yellow]")
        raise typer.Exit()

    # ------------------------------------------------------------------
    # Build canon dict
    # ------------------------------------------------------------------
    canon: dict[str, Any] = {
        "version": "1.0",
        "document": f"{system_name} Canon",
        "classification": classification,
        "audience": audience,
        "deployment_model": deployment_model,
        "leadership_briefing": {
            "executive_summary": executive_summary,
            "program_overview": program_overview,
            "modernization_need": (
                f"The {organization} requires modernization of its {deployment_model} "
                "environment to meet federal Zero Trust and FedRAMP requirements."
            ),
            "program_vision": (
                f"A fully modernized, identity-driven {deployment_model} architecture "
                "aligned with TIC 3.0, FedRAMP, SCuBA, and NIST 800-63."
            ),
            "fips_categorization": fips_categorization,
            "organization": organization,
            "control_planes": [],
            "core_concepts": [],
        },
        "components": components,
    }

    # ------------------------------------------------------------------
    # Write file
    # ------------------------------------------------------------------
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{system_slug}.yaml"

    with output_path.open("w", encoding="utf-8") as fh:
        yaml.dump(canon, fh, default_flow_style=False, allow_unicode=True, sort_keys=False)

    console.print(
        Panel.fit(
            f"[bold green]✓ Canon file written:[/bold green] [bold]{output_path}[/bold]\n\n"
            "Next steps:\n"
            f"  1. Review and edit [bold]{output_path}[/bold]\n"
            "  2. Run [bold]uiao validate-canon[/bold] to check for issues\n"
            "  3. Run [bold]uiao generate-ssp[/bold] to generate OSCAL artifacts",
            title="Done",
        )
    )
    return output_path
