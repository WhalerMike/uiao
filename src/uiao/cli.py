"""uiao CLI entry point (top-level).

Thin bridge over the existing Typer app at `uiao.impl.cli.app:app`.
As adapters migrate from `uiao.impl.*` into `uiao.*` directly, this
file can absorb those commands.

Today this enables:

    uiao --help
    uiao scuba transform --input ... --out ...
"""
from __future__ import annotations


def main() -> int:
    # Lazy import so the bridge costs nothing at package-load time.
    from uiao.impl.cli.app import app
    app()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
