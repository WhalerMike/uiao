"""Smoke test: every registered CLI command responds to --help with exit 0.

Catches import regressions across the CLI surface. New commands
are automatically covered because the test walks the Typer tree.
"""

from __future__ import annotations

import pytest
from typer.main import get_command
from typer.testing import CliRunner

from uiao.cli.app import app

runner = CliRunner()


def _walk_commands(cmd, prefix=()):
    for name, sub in cmd.commands.items():
        full = (*prefix, name)
        yield full
        if hasattr(sub, "commands") and sub.commands:
            yield from _walk_commands(sub, full)


@pytest.mark.parametrize("command_path", list(_walk_commands(get_command(app))))
def test_command_help_exits_zero(command_path: tuple[str, ...]) -> None:
    result = runner.invoke(app, [*command_path, "--help"])
    assert result.exit_code == 0, (
        f"uiao {' '.join(command_path)} --help exited {result.exit_code}\nstdout: {result.stdout}\n"
    )
