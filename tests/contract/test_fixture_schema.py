"""Tier-2 fixture schema validator.

Two-layer validation against the contract documented in
``tests/fixtures/contract/README.md``:

1. The authoritative JSON Schema lives at
   ``src/uiao/schemas/tier2-fixture/tier2-fixture.schema.json``.
   Every fixture is validated against it via ``jsonschema``.

2. Cross-cutting filesystem invariants that JSON Schema cannot express
   (the ``adapter`` field must match the parent directory name) are
   enforced as Python assertions alongside the schema check.

This is a META-test — it validates the SHAPE of fixtures, not the behavior
of any adapter. Per-adapter contract tests (``test_<adapter>_contract.py``)
that exercise the adapter against these fixtures ship per adapter as the
implementing PRs land.

Discovery is at import / collection time via ``rglob('*.yaml')`` against
``tests/fixtures/contract/``. New fixtures land under their adapter's
subdirectory and are picked up automatically — no per-fixture wiring here.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "contract"
SCHEMA_PATH = REPO_ROOT / "src" / "uiao" / "schemas" / "tier2-fixture" / "tier2-fixture.schema.json"


def _discover_fixtures() -> list[Path]:
    if not FIXTURE_ROOT.is_dir():
        return []
    return sorted({*FIXTURE_ROOT.rglob("*.yaml"), *FIXTURE_ROOT.rglob("*.yml")})


def _fixture_id(path: Path) -> str:
    return str(path.relative_to(FIXTURE_ROOT))


_FIXTURES = _discover_fixtures()
_SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
_VALIDATOR = jsonschema.Draft202012Validator(_SCHEMA)


def test_schema_self_validates() -> None:
    """The tier-2-fixture schema itself must be a valid Draft 2020-12 JSON Schema.

    Catches syntactic errors in the schema (e.g. unknown keywords, malformed
    enums) before any fixture is checked against it.
    """
    jsonschema.Draft202012Validator.check_schema(_SCHEMA)


def test_at_least_one_fixture_exists() -> None:
    """Sanity check — fail loudly if discovery returned zero fixtures.

    Without this, a tree-wipe or a path-resolution bug would silently make
    every parametrized test below collect zero cases and pass trivially.
    """
    assert _FIXTURES, (
        f"No tier-2 fixtures discovered under {FIXTURE_ROOT}. "
        "Either the directory was wiped or the path resolution is wrong."
    )


@pytest.mark.parametrize("fixture_path", _FIXTURES, ids=[_fixture_id(p) for p in _FIXTURES])
def test_fixture_validates_against_json_schema(fixture_path: Path) -> None:
    """Validate the fixture against the authoritative JSON Schema.

    Schema lives at ``src/uiao/schemas/tier2-fixture/tier2-fixture.schema.json``.
    On failure, every violation is reported (not just the first) so authoring
    errors are diagnosable from CI output alone.
    """
    text = fixture_path.read_text(encoding="utf-8")
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        pytest.fail(f"{fixture_path}: not parseable as YAML: {exc}")

    errors = sorted(_VALIDATOR.iter_errors(data), key=lambda e: e.absolute_path)
    if errors:
        formatted = "\n".join(
            f"  - [{'.'.join(str(p) for p in e.absolute_path) or '<root>'}] {e.message}" for e in errors
        )
        pytest.fail(f"{fixture_path}: schema validation failed:\n{formatted}")


@pytest.mark.parametrize("fixture_path", _FIXTURES, ids=[_fixture_id(p) for p in _FIXTURES])
def test_fixture_adapter_matches_parent_directory(fixture_path: Path) -> None:
    """Cross-cutting filesystem invariant — adapter field MUST match the
    immediate adapter directory name.

    Catches the most common authoring mistake: copying a fixture from one
    adapter and forgetting to update the adapter field. Cannot be expressed
    in the JSON Schema because it depends on filesystem context.

    Walks up the directory tree to support nested fixtures
    (e.g. entra-id/policy-targeting/<file>.yaml).
    """
    data = yaml.safe_load(fixture_path.read_text(encoding="utf-8"))
    adapter = data.get("adapter")
    adapter_dir = fixture_path.parent
    while adapter_dir.parent != FIXTURE_ROOT and adapter_dir != FIXTURE_ROOT:
        adapter_dir = adapter_dir.parent
    assert adapter == adapter_dir.name, (
        f"{fixture_path}: adapter='{adapter}' does not match adapter directory "
        f"'{adapter_dir.name}'. Each fixture must live under contract/<adapter>/."
    )
