"""Tier-2 fixture schema validator.

Per ``tests/fixtures/contract/README.md``, every YAML file under that tree
must conform to a documented contract: required top-level keys, typed
request / response blocks, an expected_behavior list, and a provenance
block citing one of the documented source classes.

This is a META-test — it validates the SHAPE of fixtures, not the behavior
of any adapter. Per-adapter contract tests (``test_<adapter>_contract.py``)
that exercise the adapter against these fixtures ship per adapter as the
implementing PRs land. This validator gates fixture authoring errors at PR
time so a malformed fixture never reaches the per-adapter test layer.

Discovery is at import / collection time via ``rglob('*.yaml')`` against
``tests/fixtures/contract/``. New fixtures land under their adapter's
subdirectory and are picked up automatically — no per-fixture wiring here.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "contract"

# Source classes documented in tests/fixtures/contract/README.md §"Source classes
# (provenance)". The fifth class is "finding-<id>" which is matched by prefix
# rather than equality (each FINDING-NNN governance finding gets its own
# canonical source identifier).
_VALID_PROVENANCE_SOURCES = {
    "microsoft-learn",
    "vendor-docs",
    "live-capture",
    "agency-sanitized",
}

# Cloud variants documented in tests/fixtures/contract/README.md §"Fixture
# contract". The README reserves these explicitly and the validator should
# reject typos (e.g. "gcc" instead of "gcc-moderate").
_VALID_CLOUD_VARIANTS = {
    "commercial",
    "gcc-moderate",
    "gcc-high",
    "dod",
    "germany",
    "china",
    "govcloud-east",
    "govcloud-west",
    "onprem",
}

_VALID_HTTP_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH"}

_REQUIRED_TOP_LEVEL_KEYS = {
    "adapter",
    "operation",
    "request",
    "response",
    "expected_behavior",
    "provenance",
}


def _discover_fixtures() -> list[Path]:
    if not FIXTURE_ROOT.is_dir():
        return []
    return sorted({*FIXTURE_ROOT.rglob("*.yaml"), *FIXTURE_ROOT.rglob("*.yml")})


def _fixture_id(path: Path) -> str:
    return str(path.relative_to(FIXTURE_ROOT))


_FIXTURES = _discover_fixtures()


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
def test_fixture_conforms_to_contract(fixture_path: Path) -> None:
    """Validate every documented clause of the tier-2 fixture contract.

    Failure messages always include the fixture path and name the violated
    clause so authoring errors are diagnosable from CI output alone.
    """
    text = fixture_path.read_text(encoding="utf-8")
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        pytest.fail(f"{fixture_path}: not parseable as YAML: {exc}")

    # ── Top-level shape ───────────────────────────────────────────
    assert isinstance(data, dict), f"{fixture_path}: top level must be a mapping, got {type(data).__name__}"
    missing = _REQUIRED_TOP_LEVEL_KEYS - set(data.keys())
    assert not missing, f"{fixture_path}: missing required top-level keys: {sorted(missing)}"

    # ── adapter must match parent directory ───────────────────────────────
    adapter = data["adapter"]
    assert isinstance(adapter, str) and adapter, f"{fixture_path}: adapter must be a non-empty string"
    # Walk up until the immediate adapter directory is found; allows nested
    # subdirectories like entra-id/policy-targeting/<file>.yaml.
    adapter_dir = fixture_path.parent
    while adapter_dir.parent != FIXTURE_ROOT and adapter_dir != FIXTURE_ROOT:
        adapter_dir = adapter_dir.parent
    assert adapter == adapter_dir.name, (
        f"{fixture_path}: adapter='{adapter}' does not match adapter directory "
        f"'{adapter_dir.name}'. Each fixture must live under contract/<adapter>/."
    )

    # ── operation ──────────────────────────────────────────────────
    operation = data["operation"]
    assert isinstance(operation, str) and operation, f"{fixture_path}: operation must be a non-empty string"

    # ── request block ────────────────────────────────────────────────
    req = data["request"]
    assert isinstance(req, dict), f"{fixture_path}: request must be a mapping"
    method = req.get("method")
    assert method in _VALID_HTTP_METHODS, (
        f"{fixture_path}: request.method='{method}' must be one of {sorted(_VALID_HTTP_METHODS)}"
    )
    url = req.get("url")
    assert isinstance(url, str) and url.startswith(("http://", "https://")), (
        f"{fixture_path}: request.url must be an absolute http(s) URL"
    )
    headers = req.get("headers")
    assert headers is None or isinstance(headers, dict), f"{fixture_path}: request.headers must be a mapping or null"

    # ── response block ───────────────────────────────────────────────
    resp = data["response"]
    assert isinstance(resp, dict), f"{fixture_path}: response must be a mapping"
    status = resp.get("status")
    assert isinstance(status, int) and 100 <= status < 600, (
        f"{fixture_path}: response.status='{status}' must be an integer HTTP status code"
    )

    # ── expected_behavior ─────────────────────────────────────────────
    eb = data["expected_behavior"]
    assert isinstance(eb, list) and eb, f"{fixture_path}: expected_behavior must be a non-empty list"
    for i, item in enumerate(eb):
        assert isinstance(item, str) and item.strip(), (
            f"{fixture_path}: expected_behavior[{i}] must be a non-empty string"
        )

    # ── provenance ───────────────────────────────────────────────────
    prov = data["provenance"]
    assert isinstance(prov, dict), f"{fixture_path}: provenance must be a mapping"
    source = prov.get("source")
    assert isinstance(source, str) and source, f"{fixture_path}: provenance.source required"
    if source not in _VALID_PROVENANCE_SOURCES and not source.startswith("finding-"):
        pytest.fail(
            f"{fixture_path}: provenance.source='{source}' must be one of "
            f"{sorted(_VALID_PROVENANCE_SOURCES)} OR a 'finding-<id>' identifier"
        )

    # ── cloud_variant (optional) ─────────────────────────────────────────
    cv = data.get("cloud_variant")
    if cv is not None:
        assert isinstance(cv, list) and cv, f"{fixture_path}: cloud_variant must be a non-empty list when present"
        for i, item in enumerate(cv):
            assert item in _VALID_CLOUD_VARIANTS, (
                f"{fixture_path}: cloud_variant[{i}]='{item}' must be one of {sorted(_VALID_CLOUD_VARIANTS)}"
            )
