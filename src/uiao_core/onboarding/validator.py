"""Pre-generation canon YAML completeness validator.

Checks a canon YAML file for required fields, validates field values, and
reports missing or invalid entries with actionable suggestions before any
document generation is attempted.

Usage::

    uiao validate-canon --canon canon/my_system.yaml
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from rich.console import Console
from rich.table import Table

console = Console()

# ---------------------------------------------------------------------------
# Required-field specification
# ---------------------------------------------------------------------------

# Each tuple is (dot-separated field path, example value, description)
_REQUIRED_FIELDS: list[tuple[str, str, str]] = [
    ("version", "1.0", "Canon schema version"),
    ("document", "My System Canon", "Human-readable document title"),
    ("classification", "CUI//SP-CTI", "Document classification marking"),
    ("audience", "[CIO, CISO, PMO]", "List of target audience roles"),
    ("deployment_model", "azure | aws | hybrid | on_prem", "CSP / deployment model"),
    ("leadership_briefing.executive_summary", "One-sentence description…", "Executive summary text"),
    ("leadership_briefing.program_overview", "Detailed overview paragraph…", "Program overview text"),
    ("leadership_briefing.organization", "Department of X", "Owning organization name"),
    ("leadership_briefing.fips_categorization", "moderate", "FIPS 199 impact level"),
]

_VALID_DEPLOYMENT_MODELS = {"azure", "aws", "hybrid", "on_prem"}
_VALID_FIPS = {"low", "moderate", "high"}


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class ValidationIssue:
    """A single validation finding."""

    severity: str  # "error" | "warning" | "info"
    field: str
    message: str
    suggestion: str = ""


@dataclass
class ValidationResult:
    """Aggregated result of a canon validation run."""

    canon_path: Path
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == "warning"]

    @property
    def passed(self) -> bool:
        return len(self.errors) == 0


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_nested(data: dict[str, Any], dotted_key: str) -> tuple[bool, Any]:
    """Return (found, value) for a dot-separated key path."""
    parts = dotted_key.split(".")
    current: Any = data
    for part in parts:
        if not isinstance(current, dict) or part not in current:
            return False, None
        current = current[part]
    return True, current


def _check_required_fields(data: dict[str, Any]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for dotted, example, description in _REQUIRED_FIELDS:
        found, value = _get_nested(data, dotted)
        if not found or value is None or value == "" or value == []:
            issues.append(
                ValidationIssue(
                    severity="error",
                    field=dotted,
                    message=f"Missing or empty required field: {description}",
                    suggestion=f"Add  {dotted}: {example}  to your canon YAML.",
                )
            )
    return issues


def _check_value_constraints(data: dict[str, Any]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    # deployment_model
    found, dm = _get_nested(data, "deployment_model")
    if found and dm and str(dm).lower() not in _VALID_DEPLOYMENT_MODELS:
        issues.append(
            ValidationIssue(
                severity="error",
                field="deployment_model",
                message=f"Invalid deployment_model value: '{dm}'",
                suggestion=(f"Allowed values: {', '.join(sorted(_VALID_DEPLOYMENT_MODELS))}"),
            )
        )

    # fips_categorization
    found, fips = _get_nested(data, "leadership_briefing.fips_categorization")
    if found and fips and str(fips).lower() not in _VALID_FIPS:
        issues.append(
            ValidationIssue(
                severity="error",
                field="leadership_briefing.fips_categorization",
                message=f"Invalid fips_categorization value: '{fips}'",
                suggestion=(f"Allowed values: {', '.join(sorted(_VALID_FIPS))}"),
            )
        )

    # audience must be a list
    found, audience = _get_nested(data, "audience")
    if found and audience is not None and not isinstance(audience, list):
        issues.append(
            ValidationIssue(
                severity="error",
                field="audience",
                message="'audience' must be a YAML list, not a scalar string.",
                suggestion="Use:\n  audience:\n    - CIO\n    - CISO",
            )
        )

    return issues


def _check_optional_sections(data: dict[str, Any]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    # control_planes — warn if absent or empty
    found, cp = _get_nested(data, "leadership_briefing.control_planes")
    if not found or not cp:
        issues.append(
            ValidationIssue(
                severity="warning",
                field="leadership_briefing.control_planes",
                message="No control_planes defined — generated documents will omit architecture sections.",
                suggestion="Add a control_planes list under leadership_briefing.",
            )
        )

    # components — warn if absent
    found, comps = _get_nested(data, "components")
    if not found or not comps:
        issues.append(
            ValidationIssue(
                severity="info",
                field="components",
                message="No top-level components list found.",
                suggestion="Add a components list with name/role entries for inventory generation.",
            )
        )

    return issues


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate_canon(canon_path: Path) -> ValidationResult:
    """Validate a canon YAML file and return a :class:`ValidationResult`.

    Parameters
    ----------
    canon_path:
        Path to the canon YAML file to validate.

    Returns
    -------
    ValidationResult
        Object containing all :class:`ValidationIssue` findings.
    """
    result = ValidationResult(canon_path=canon_path)

    if not canon_path.exists():
        result.issues.append(
            ValidationIssue(
                severity="error",
                field="file",
                message=f"Canon file not found: {canon_path}",
                suggestion="Check the path and try again.",
            )
        )
        return result

    try:
        with canon_path.open(encoding="utf-8") as fh:
            data: dict[str, Any] = yaml.safe_load(fh) or {}
    except yaml.YAMLError as exc:
        result.issues.append(
            ValidationIssue(
                severity="error",
                field="file",
                message=f"YAML parse error: {exc}",
                suggestion="Fix the syntax error and re-run validation.",
            )
        )
        return result

    result.issues.extend(_check_required_fields(data))
    result.issues.extend(_check_value_constraints(data))
    result.issues.extend(_check_optional_sections(data))
    return result


def print_validation_report(result: ValidationResult) -> None:
    """Print a formatted validation report to the console.

    Parameters
    ----------
    result:
        A :class:`ValidationResult` produced by :func:`validate_canon`.
    """
    icon_map = {"error": "[red]✗[/red]", "warning": "[yellow]⚠[/yellow]", "info": "[dim]ℹ[/dim]"}
    color_map = {"error": "red", "warning": "yellow", "info": "dim"}

    console.print(f"\n[bold]Canon validation report:[/bold] {result.canon_path}\n")

    if not result.issues:
        console.print("[bold green]✓ All checks passed — canon file looks good![/bold green]")
        return

    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
    table.add_column("", width=2)
    table.add_column("Field", style="bold")
    table.add_column("Issue")
    table.add_column("Suggestion", style="dim")

    for issue in result.issues:
        icon = icon_map.get(issue.severity, "?")
        color = color_map.get(issue.severity, "white")
        table.add_row(
            icon,
            f"[{color}]{issue.field}[/{color}]",
            f"[{color}]{issue.message}[/{color}]",
            issue.suggestion,
        )

    console.print(table)

    nerr = len(result.errors)
    nwarn = len(result.warnings)
    ninfo = len([i for i in result.issues if i.severity == "info"])

    parts = []
    if nerr:
        parts.append(f"[red]{nerr} error(s)[/red]")
    if nwarn:
        parts.append(f"[yellow]{nwarn} warning(s)[/yellow]")
    if ninfo:
        parts.append(f"[dim]{ninfo} info[/dim]")

    console.print("\n" + "  ".join(parts))
    if not result.passed:
        console.print("[red]Validation failed. Fix the errors above before running generators.[/red]")
    else:
        console.print("[green]Validation passed with warnings. Review suggestions above.[/green]")
