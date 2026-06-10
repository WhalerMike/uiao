"""Active Governance Directory CLI: ``uiao directory ...`` (ADR-099).

Thin verbs over :mod:`uiao.directory`:

- ``tree`` — project a principal snapshot into the read-only Directory
  Information Tree and emit it as LDIF (inspection / diffing).
- ``serve`` — run the in-path LDAPv3 read projection over TCP.

A *principal snapshot* is the OrgPath governance-runtime shape::

    {"principals": [{"principal_id": "...", "principal_type": "user",
                     "attributes": {"extensionAttribute1": "NCR", ...}}]}

Canon: ADR-099 (data-plane exception), UIAO_151 (codebook),
UIAO_193 / ADR-098 (the ``ldap`` binding profile).
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import typer
from rich.console import Console

from uiao.directory import build_directory
from uiao.directory.dit import Directory
from uiao.directory.server import LdapServer

directory_app = typer.Typer(
    name="directory",
    help="Active Governance Directory — in-path LDAPv3 read projection (ADR-099).",
    no_args_is_help=True,
)

console = Console()

_SNAPSHOT_OPT = typer.Option(
    None,
    "--snapshot",
    "-s",
    help='Path to a principal-snapshot JSON file ({"principals": [...]}).',
)
_BASE_DN_OPT = typer.Option("dc=agd,dc=uiao,dc=gov", "--base-dn", "-b", help="Directory suffix (base DN).")


def _load_principals(snapshot: Path | None) -> list[dict]:
    if snapshot is None:
        return []
    if not snapshot.exists():
        console.print(f"[red]Snapshot not found:[/red] {snapshot}")
        raise typer.Exit(code=1)
    try:
        payload = json.loads(snapshot.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        console.print(f"[red]Invalid JSON in snapshot:[/red] {exc}")
        raise typer.Exit(code=1) from exc
    principals = payload.get("principals") if isinstance(payload, dict) else None
    if not isinstance(principals, list):
        console.print("[red]Snapshot must be an object with a 'principals' list.[/red]")
        raise typer.Exit(code=1)
    return principals


def _to_ldif(directory: Directory) -> str:
    lines: list[str] = []
    for entry in directory.entries:
        lines.append(f"dn: {entry.dn}")
        for name, values in entry.attributes.items():
            for value in values:
                lines.append(f"{name}: {value}")
        lines.append("")
    return "\n".join(lines)


@directory_app.command("tree")
def tree(
    snapshot: Path | None = _SNAPSHOT_OPT,
    base_dn: str = _BASE_DN_OPT,
) -> None:
    """Project a snapshot into the DIT and print it as LDIF."""
    principals = _load_principals(snapshot)
    directory = build_directory(principals, base_dn=base_dn)
    console.print(_to_ldif(directory))


@directory_app.command("serve")
def serve(
    snapshot: Path | None = _SNAPSHOT_OPT,
    base_dn: str = _BASE_DN_OPT,
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Bind address."),
    port: int = typer.Option(3389, "--port", "-p", help="Bind port (default 3389 — unprivileged)."),
    check: bool = typer.Option(
        False,
        "--check",
        help="Build the projection and print the listen plan without binding (CI-friendly).",
    ),
) -> None:
    """Run the in-path LDAPv3 read projection (ADR-099)."""
    principals = _load_principals(snapshot)
    directory = build_directory(principals, base_dn=base_dn)
    server = LdapServer(directory=directory)
    entry_count = len(directory.entries)
    if check:
        console.print(
            f"[green]OK[/green] — would serve {entry_count} entries "
            f"(suffix {base_dn}) on ldap://{host}:{port} (read-only)."
        )
        return
    console.print(
        f"[green]Active Governance Directory[/green] serving {entry_count} entries "
        f"on ldap://{host}:{port} (read-only). Ctrl-C to stop."
    )
    try:
        asyncio.run(server.serve(host=host, port=port))
    except KeyboardInterrupt:  # pragma: no cover - interactive only
        console.print("\nstopped.")
