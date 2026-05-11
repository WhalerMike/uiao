"""uiao.cli.reciprocity — Typer sub-app for ``uiao reciprocity`` command group.

Mount point
-----------
    # in uiao/cli/app.py
    from uiao.cli.reciprocity import reciprocity_app
    app.add_typer(reciprocity_app, name="reciprocity")

Usage (after ``pip install -e .``)
-----------------------------------
    uiao reciprocity onboard-agency \\
        --controlling-ato OPM-HRIT-2026-001 \\
        --consuming-agency TREAS \\
        --legal-basis interagency-mou \\
        --configuration-latitude-ref ssp-2026-latitude-baseline-v1 \\
        --out-dir /tmp/hrit-recip

    uiao reciprocity list-records --records-dir /tmp/hrit-recip

    uiao reciprocity verify --record /tmp/hrit-recip/TREAS/reciprocity-record.json
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

reciprocity_app = typer.Typer(
    name="reciprocity",
    help="HRIT Single-ATO Reciprocity operations (UIAO_140 / ADR-054).",
    add_completion=False,
)

_console = Console()

_WS_A2_NOT_MERGED_MSG = "WS-A2 emitter not yet merged; run after Phase 2 integration"
_WS_A2_EXIT_CODE = 3


class LegalBasis(str, Enum):
    """Enumeration of valid legal-basis values for a reciprocity record."""

    interagency_mou = "interagency-mou"
    economy_act = "economy-act"
    fisma_shared_service = "fisma-shared-service"
    fedramp_authorization = "fedramp-authorization"
    other_statutory_authority = "other-statutory-authority"


# ---------------------------------------------------------------------------
# onboard-agency
# ---------------------------------------------------------------------------


@reciprocity_app.command("onboard-agency")
def onboard_agency(
    controlling_ato: str = typer.Option(
        ...,
        "--controlling-ato",
        help="Identifier of the controlling ATO (e.g. OPM-HRIT-2026-001).",
        show_default=False,
    ),
    consuming_agency: str = typer.Option(
        ...,
        "--consuming-agency",
        help="Two-to-six character agency code for the consuming agency (e.g. TREAS).",
        show_default=False,
    ),
    legal_basis: LegalBasis = typer.Option(
        ...,
        "--legal-basis",
        help=("Legal basis for reciprocity. One of: " + ", ".join(v.value for v in LegalBasis) + "."),
        show_default=False,
    ),
    reciprocity_basis: str = typer.Option(
        "interagency-reciprocity",
        "--reciprocity-basis",
        help="Reciprocity basis identifier string.",
    ),
    effective_at: Optional[str] = typer.Option(
        None,
        "--effective-at",
        help="ISO-8601 datetime at which the record becomes effective (default: now).",
    ),
    expires_at: Optional[str] = typer.Option(
        None,
        "--expires-at",
        help="ISO-8601 datetime at which the record expires (default: now + 365 days).",
    ),
    configuration_latitude_ref: str = typer.Option(
        ...,
        "--configuration-latitude-ref",
        help="Reference identifier for the SSP configuration-latitude baseline.",
        show_default=False,
    ),
    signer: Optional[str] = typer.Option(
        None,
        "--signer",
        help="Signer identity (default: $USER env var or 'uiao-reciprocity-operator').",
    ),
    out_dir: Path = typer.Option(
        Path("reciprocity-records"),
        "--out-dir",
        help="Output directory root; record is written to <out-dir>/<consuming-agency>/reciprocity-record.json.",
    ),
    signing_key_env: str = typer.Option(
        "UIAO_RECIPROCITY_HMAC_KEY",
        "--signing-key-env",
        help="Name of the environment variable that holds the HMAC signing key.",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Print the record that would be emitted; do not write to disk.",
    ),
) -> None:
    """Emit a reciprocity record for a consuming agency.

    Calls the WS-A2 emitter (``uiao.oscal.reciprocity_record.emit_reciprocity_record``).
    If the emitter module is not yet available (Phase 2 not yet merged), the
    command exits with code 3 and an informative message.

    \\b
    Example
    -------

        uiao reciprocity onboard-agency \\
            --controlling-ato OPM-HRIT-2026-001 \\
            --consuming-agency TREAS \\
            --legal-basis interagency-mou \\
            --configuration-latitude-ref ssp-2026-latitude-baseline-v1 \\
            --out-dir /tmp/hrit-recip
    """
    # Resolve defaults that depend on runtime state.
    now = datetime.now(tz=timezone.utc)

    effective_dt: datetime
    if effective_at is not None:
        try:
            effective_dt = datetime.fromisoformat(effective_at)
        except ValueError as exc:
            _console.print(f"[red]Invalid --effective-at datetime: {exc}[/red]")
            raise typer.Exit(code=1) from exc
    else:
        effective_dt = now

    expires_dt: datetime
    if expires_at is not None:
        try:
            expires_dt = datetime.fromisoformat(expires_at)
        except ValueError as exc:
            _console.print(f"[red]Invalid --expires-at datetime: {exc}[/red]")
            raise typer.Exit(code=1) from exc
    else:
        expires_dt = now + timedelta(days=365)

    resolved_signer = signer or os.environ.get("USER") or "uiao-reciprocity-operator"

    record_params: dict = {
        "controlling_ato_id": controlling_ato,
        "consuming_agency_code": consuming_agency,
        "legal_basis": legal_basis.value,
        "reciprocity_basis": reciprocity_basis,
        "effective_at": effective_dt.isoformat(),
        "expires_at": expires_dt.isoformat(),
        "configuration_latitude_ref": configuration_latitude_ref,
        "signer": resolved_signer,
        "signing_key_env": signing_key_env,
    }

    # Try to import the WS-A2 emitter.
    try:
        from uiao.oscal.reciprocity_record import emit_reciprocity_record  # type: ignore[import]
    except ImportError as exc:
        _console.print(f"[red]{_WS_A2_NOT_MERGED_MSG}[/red]")
        raise typer.Exit(code=_WS_A2_EXIT_CODE) from exc

    if dry_run:
        _console.print("[bold yellow]--dry-run: would emit record (not writing to disk)[/bold yellow]")
        _console.print(json.dumps(record_params, indent=2, ensure_ascii=False))
        return

    dest_dir = out_dir / consuming_agency
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_file = dest_dir / "reciprocity-record.json"

    try:
        record = emit_reciprocity_record(**record_params)
        dest_file.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
        _console.print(f"[green]Reciprocity record written to {dest_file}[/green]")
    except Exception as exc:  # noqa: BLE001
        _console.print(f"[red]Failed to emit reciprocity record: {exc}[/red]")
        raise typer.Exit(code=1) from exc


# ---------------------------------------------------------------------------
# list-records
# ---------------------------------------------------------------------------


@reciprocity_app.command("list-records")
def list_records(
    records_dir: Path = typer.Option(
        ...,
        "--records-dir",
        help="Root directory containing per-agency reciprocity-record.json files.",
        show_default=False,
    ),
    emit_json: bool = typer.Option(
        False,
        "--json",
        help="Emit records as JSON array on stdout instead of a rich table.",
    ),
) -> None:
    """Enumerate reciprocity records and display their status.

    Walks ``<records-dir>/**/reciprocity-record.json`` and prints a table
    of (controlling_ato_id, consuming_agency_code, effective_at, expires_at,
    status).  Status is computed as ``Active`` or ``Expired`` relative to the
    current UTC time.

    \\b
    Example
    -------

        uiao reciprocity list-records --records-dir /tmp/hrit-recip

        uiao reciprocity list-records --records-dir /tmp/hrit-recip --json
    """
    now = datetime.now(tz=timezone.utc)

    if not records_dir.exists():
        _console.print(f"[yellow]Records directory does not exist: {records_dir}[/yellow]")
        _console.print("no records found")
        return

    record_files = sorted(records_dir.rglob("reciprocity-record.json"))
    if not record_files:
        _console.print("no records found")
        return

    rows: list[dict] = []
    for record_file in record_files:
        try:
            data = json.loads(record_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            _console.print(f"[yellow]Skipping unreadable file {record_file}: {exc}[/yellow]")
            continue

        controlling_ato_id = str(data.get("controlling_ato_id", data.get("controlling_ato", "")))
        consuming_agency_code = str(data.get("consuming_agency_code", data.get("consuming_agency", "")))
        effective_at_raw = str(data.get("effective_at", ""))
        expires_at_raw = str(data.get("expires_at", ""))

        status = "Unknown"
        if expires_at_raw:
            try:
                expires_dt = datetime.fromisoformat(expires_at_raw)
                if expires_dt.tzinfo is None:
                    expires_dt = expires_dt.replace(tzinfo=timezone.utc)
                status = "Active" if expires_dt > now else "Expired"
            except ValueError:
                status = "Unknown"

        rows.append(
            {
                "controlling_ato_id": controlling_ato_id,
                "consuming_agency_code": consuming_agency_code,
                "effective_at": effective_at_raw,
                "expires_at": expires_at_raw,
                "status": status,
                "file": str(record_file),
            }
        )

    if emit_json:
        typer.echo(json.dumps(rows, indent=2, ensure_ascii=False))
        return

    table = Table(show_header=True, header_style="bold blue")
    table.add_column("controlling_ato_id")
    table.add_column("consuming_agency_code")
    table.add_column("effective_at")
    table.add_column("expires_at")
    table.add_column("status")

    for row in rows:
        status_val = row["status"]
        status_style = {"Active": "green", "Expired": "red"}.get(status_val, "yellow")
        table.add_row(
            row["controlling_ato_id"],
            row["consuming_agency_code"],
            row["effective_at"],
            row["expires_at"],
            f"[{status_style}]{status_val}[/{status_style}]",
        )

    _console.print(table)
    _console.print(f"[dim]{len(rows)} record(s) found[/dim]")


# ---------------------------------------------------------------------------
# verify
# ---------------------------------------------------------------------------


@reciprocity_app.command("verify")
def verify(
    record: Path = typer.Option(
        ...,
        "--record",
        help="Path to a reciprocity-record.json file to verify.",
        show_default=False,
    ),
    signing_key_env: str = typer.Option(
        "UIAO_RECIPROCITY_HMAC_KEY",
        "--signing-key-env",
        help="Name of the environment variable that holds the HMAC signing key.",
    ),
) -> None:
    """Verify the HMAC signature of a reciprocity record.

    Calls the WS-A2 verifier (``uiao.oscal.reciprocity_record.verify_signature``).
    If the verifier module is not yet available (Phase 2 not yet merged), the
    command exits with code 3 and an informative message.

    Exit codes:
        0 — signature valid
        1 — signature invalid or record unreadable
        3 — WS-A2 verifier not yet merged

    \\b
    Example
    -------

        uiao reciprocity verify \\
            --record /tmp/hrit-recip/TREAS/reciprocity-record.json \\
            --signing-key-env UIAO_RECIPROCITY_HMAC_KEY
    """
    # Try to import the WS-A2 verifier.
    try:
        from uiao.oscal.reciprocity_record import verify_signature  # type: ignore[import]
    except ImportError as exc:
        _console.print(f"[red]{_WS_A2_NOT_MERGED_MSG}[/red]")
        raise typer.Exit(code=_WS_A2_EXIT_CODE) from exc

    if not record.exists():
        _console.print(f"[red]Record file not found: {record}[/red]")
        raise typer.Exit(code=1)

    try:
        data = json.loads(record.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        _console.print(f"[red]Failed to read record: {exc}[/red]")
        raise typer.Exit(code=1) from exc

    signing_key = os.environ.get(signing_key_env)

    try:
        valid = verify_signature(data, signing_key=signing_key)  # type: ignore[arg-type]
    except Exception as exc:  # noqa: BLE001
        _console.print(f"[red]Verification error: {exc}[/red]")
        raise typer.Exit(code=1) from exc

    if valid:
        _console.print("[green]Signature valid.[/green]")
    else:
        _console.print("[red]Signature INVALID.[/red]")
        raise typer.Exit(code=1)
