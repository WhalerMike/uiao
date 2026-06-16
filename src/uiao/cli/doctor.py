"""uiao.cli.doctor — Typer sub-app for the `uiao doctor` command.

Mount point
-----------
    # in uiao/cli/app.py
    from uiao.cli.doctor import doctor_app
    app.add_typer(doctor_app, name="doctor")

Usage (after ``pip install -e .``)
-----------------------------------
    uiao doctor
"""

from __future__ import annotations

import os
import sys
import urllib.request
from typing import List, Tuple

import typer
from rich.console import Console
from rich.table import Table

from uiao.__version__ import __version__

doctor_app = typer.Typer(
    name="doctor",
    help="Self-check: report PASS/FAIL/WARN for environment and dependencies.",
    add_completion=False,
    invoke_without_command=True,
)

_console = Console()

# Result constants
PASS = "PASS"
FAIL = "FAIL"
WARN = "WARN"

_STATUS_STYLE = {
    PASS: "bold green",
    FAIL: "bold red",
    WARN: "bold yellow",
}


def _check(label: str, status: str, detail: str) -> Tuple[str, str, str]:
    return label, status, detail


def _run_checks() -> List[Tuple[str, str, str]]:
    results: List[Tuple[str, str, str]] = []

    # 1. Python version
    major, minor = sys.version_info.major, sys.version_info.minor
    if (major, minor) >= (3, 10):
        results.append(
            _check(
                "Python version",
                PASS,
                f"{major}.{minor}.{sys.version_info.micro} (>= 3.10 required)",
            )
        )
    else:
        results.append(
            _check(
                "Python version",
                FAIL,
                f"{major}.{minor}.{sys.version_info.micro} — 3.10+ required",
            )
        )

    # 2. Required env vars
    required_vars = [
        "UIAO_WORKSPACE_ROOT",
        "UIAO_ENTRA_TENANT_ID",
        "UIAO_ENTRA_CLIENT_ID",
        "UIAO_ENTRA_CLIENT_SECRET",
    ]
    for var in required_vars:
        val = os.environ.get(var)
        if val:
            results.append(_check(f"Env: {var}", PASS, "set"))
        else:
            results.append(_check(f"Env: {var}", FAIL, "not set"))

    # 3. UIAO_WORKSPACE_ROOT exists on disk
    workspace = os.environ.get("UIAO_WORKSPACE_ROOT", "")
    if not workspace:
        results.append(
            _check(
                "UIAO_WORKSPACE_ROOT on disk",
                WARN,
                "UIAO_WORKSPACE_ROOT not set — skipping path check",
            )
        )
    elif os.path.isdir(workspace):
        results.append(
            _check(
                "UIAO_WORKSPACE_ROOT on disk",
                PASS,
                workspace,
            )
        )
    else:
        results.append(
            _check(
                "UIAO_WORKSPACE_ROOT on disk",
                FAIL,
                f"{workspace!r} does not exist",
            )
        )

    # 4. uiao.api importable
    try:
        import uiao.api  # noqa: F401

        results.append(_check("uiao.api [api] extra", PASS, "importable"))
    except ImportError:
        results.append(_check("uiao.api [api] extra", WARN, "not installed (pip install uiao[api])"))

    # 5. uiao.saas importable
    try:
        import uiao.saas  # noqa: F401

        results.append(_check("uiao.saas [saas] extra", PASS, "importable"))
    except ImportError:
        results.append(_check("uiao.saas [saas] extra", WARN, "not installed (pip install uiao[saas])"))

    # 6. Entra connectivity (network reachability only)
    try:
        req = urllib.request.Request(
            "https://login.microsoftonline.com",
            method="HEAD",
            headers={"User-Agent": f"uiao/{__version__}"},
        )
        with urllib.request.urlopen(req, timeout=5):
            pass
        results.append(
            _check(
                "Entra connectivity",
                PASS,
                "login.microsoftonline.com reachable",
            )
        )
    except Exception as exc:
        results.append(
            _check(
                "Entra connectivity",
                FAIL,
                f"login.microsoftonline.com unreachable: {exc}",
            )
        )

    # 7. Schema validity
    try:
        import uiao.schemas  # noqa: F401

        results.append(_check("uiao.schemas", PASS, "importable"))
    except ImportError:
        results.append(_check("uiao.schemas", WARN, "not importable"))
    except Exception as exc:
        results.append(_check("uiao.schemas", FAIL, f"error: {exc}"))

    return results


@doctor_app.callback()
def doctor() -> None:
    """Run environment self-checks and print a PASS/FAIL/WARN report."""
    results = _run_checks()

    table = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 2))
    table.add_column("Check", style="dim", min_width=32)
    table.add_column("Status", min_width=6)
    table.add_column("Detail")

    fail_count = 0
    for label, status, detail in results:
        style = _STATUS_STYLE.get(status, "")
        table.add_row(label, f"[{style}]{status}[/{style}]", detail)
        if status == FAIL:
            fail_count += 1

    _console.print()
    _console.print(table)
    _console.print()

    if fail_count == 0:
        _console.print("[bold green]All checks passed.[/bold green]")
    else:
        _console.print(f"[bold red]{fail_count} check{'s' if fail_count > 1 else ''} failed — see above.[/bold red]")
    _console.print()
    raise typer.Exit(code=fail_count)
