"""Active Governance Directory CLI: ``uiao directory ...`` (ADR-100).

Thin verbs over :mod:`uiao.directory`:

- ``tree`` — project a principal snapshot into the read-only Directory
  Information Tree and emit it as LDIF (inspection / diffing).
- ``serve`` — run the in-path LDAPv3 read projection over TCP.

A *principal snapshot* is the OrgPath governance-runtime shape::

    {"principals": [{"principal_id": "...", "principal_type": "user",
                     "attributes": {"extensionAttribute1": "NCR", ...}}]}

Canon: ADR-100 (data-plane exception), UIAO_151 (codebook),
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
from uiao.directory.server import LdapServer, build_server_tls_context

directory_app = typer.Typer(
    name="directory",
    help="Active Governance Directory — in-path LDAPv3 read projection (ADR-100).",
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
    port: int = typer.Option(0, "--port", "-p", help="Bind port (default 1389 plaintext, 636 with TLS)."),
    tls_cert: Path | None = typer.Option(None, "--tls-cert", help="PEM certificate for TLS (requires --tls-key)."),
    tls_key: Path | None = typer.Option(None, "--tls-key", help="PEM private key for TLS (requires --tls-cert)."),
    starttls: bool = typer.Option(
        False,
        "--starttls",
        help="Serve plaintext but offer the StartTLS in-band upgrade (vs. LDAPS-on-connect).",
    ),
    check: bool = typer.Option(
        False,
        "--check",
        help="Build the projection and print the listen plan without binding (CI-friendly).",
    ),
) -> None:
    """Run the in-path LDAPv3 read projection (ADR-100)."""
    if bool(tls_cert) ^ bool(tls_key):
        console.print("[red]--tls-cert and --tls-key must be supplied together.[/red]")
        raise typer.Exit(code=1)
    if starttls and tls_cert is None:
        console.print("[red]--starttls requires --tls-cert/--tls-key.[/red]")
        raise typer.Exit(code=1)
    have_cert = tls_cert is not None
    ldaps = have_cert and not starttls  # LDAPS-on-connect vs. StartTLS-on-plaintext
    effective_port = port if port else (636 if ldaps else 1389)
    if ldaps:
        scheme = "ldaps"
    elif starttls:
        scheme = "ldap+starttls"
    else:
        scheme = "ldap"

    principals = _load_principals(snapshot)
    directory = build_directory(principals, base_dn=base_dn)
    server = LdapServer(directory=directory)
    entry_count = len(directory.entries)
    if check:
        console.print(
            f"[green]OK[/green] — would serve {entry_count} entries "
            f"(suffix {base_dn}) on {scheme}://{host}:{effective_port} (read-only)."
        )
        return

    ssl_context = None
    if have_cert:
        assert tls_cert is not None and tls_key is not None
        if not tls_cert.exists() or not tls_key.exists():
            console.print("[red]TLS cert or key file not found.[/red]")
            raise typer.Exit(code=1)
        context = build_server_tls_context(str(tls_cert), str(tls_key))
        if starttls:
            server.tls_context = context  # in-band upgrade on the plaintext port
        else:
            ssl_context = context  # TLS-on-connect

    console.print(
        f"[green]Active Governance Directory[/green] serving {entry_count} entries "
        f"on {scheme}://{host}:{effective_port} (read-only). Ctrl-C to stop."
    )
    try:
        asyncio.run(server.serve(host=host, port=effective_port, ssl_context=ssl_context))
    except KeyboardInterrupt:  # pragma: no cover - interactive only
        console.print("\nstopped.")
