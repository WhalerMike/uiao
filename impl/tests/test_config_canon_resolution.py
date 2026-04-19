"""
Regression tests for canon-root resolution in `uiao.impl.config`.

Pins the post-consolidation monorepo behavior where canon content is
split across two locations:

- `core/data`, `core/compliance` — reference data
- `src/uiao/rules`, `src/uiao/schemas` — governance SSOT

See: GitHub issue #99.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest


def _build_fake_monorepo(tmp_path: Path) -> Path:
    """Scaffold a fake monorepo with the real directory shape.

    Returns the `impl/` subdirectory (the intended CWD for running
    pytest / the CLI).
    """
    (tmp_path / "core" / "data").mkdir(parents=True)
    (tmp_path / "core" / "compliance").mkdir(parents=True)
    (tmp_path / "src" / "uiao" / "rules" / "ksi").mkdir(parents=True)
    (tmp_path / "src" / "uiao" / "schemas").mkdir(parents=True)
    impl_dir = tmp_path / "impl"
    impl_dir.mkdir()
    return impl_dir


@pytest.fixture
def fresh_config(monkeypatch: pytest.MonkeyPatch):
    """Reload `uiao.impl.config` so each test observes a clean CWD."""
    monkeypatch.delenv("UIAO_CANON_PATH", raising=False)
    yield
    import uiao.impl.config as cfg
    importlib.reload(cfg)


def test_resolve_canon_roots_finds_both_core_and_src_uiao(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fresh_config,
) -> None:
    impl_dir = _build_fake_monorepo(tmp_path)
    monkeypatch.chdir(impl_dir)

    import uiao.impl.config as cfg
    importlib.reload(cfg)

    roots = cfg._resolve_canon_roots()
    assert len(roots) == 2
    assert roots[0].name == "core"
    assert roots[1] == tmp_path / "src" / "uiao"


def test_settings_routes_rules_dir_to_src_uiao(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fresh_config,
) -> None:
    impl_dir = _build_fake_monorepo(tmp_path)
    monkeypatch.chdir(impl_dir)

    import uiao.impl.config as cfg
    importlib.reload(cfg)

    settings = cfg.Settings()
    assert settings.rules_dir == tmp_path / "src" / "uiao" / "rules"
    assert settings.schemas_dir == tmp_path / "src" / "uiao" / "schemas"


def test_settings_routes_data_dir_to_core(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fresh_config,
) -> None:
    impl_dir = _build_fake_monorepo(tmp_path)
    monkeypatch.chdir(impl_dir)

    import uiao.impl.config as cfg
    importlib.reload(cfg)

    settings = cfg.Settings()
    assert settings.data_dir == tmp_path / "core" / "data"
    assert settings.compliance_dir == tmp_path / "core" / "compliance"


def test_env_override_wins(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fresh_config,
) -> None:
    impl_dir = _build_fake_monorepo(tmp_path)
    explicit_root = tmp_path / "elsewhere"
    (explicit_root / "rules").mkdir(parents=True)
    monkeypatch.chdir(impl_dir)
    monkeypatch.setenv("UIAO_CANON_PATH", str(explicit_root))

    import uiao.impl.config as cfg
    importlib.reload(cfg)

    roots = cfg._resolve_canon_roots()
    assert roots == [explicit_root]

    settings = cfg.Settings()
    assert settings.rules_dir == explicit_root / "rules"


def test_ksi_library_loads_163_entries_end_to_end(
    monkeypatch: pytest.MonkeyPatch,
    fresh_config,
) -> None:
    """Integration check against the real monorepo canon.

    Runs the actual `load_ksi_library()` from the running repo to pin the
    post-consolidation wiring end to end. If this test fails, the
    SCuBA→IR pipeline will silently produce unmapped evidence.
    """
    import uiao.impl.config as cfg
    importlib.reload(cfg)

    repo_root = Path(__file__).resolve().parents[2]
    impl_dir = repo_root / "impl"
    if not (impl_dir / "src").is_dir():
        pytest.skip("expected monorepo layout not found")
    monkeypatch.chdir(impl_dir)
    importlib.reload(cfg)

    from uiao.impl.ir.mapping import ksi_to_ir
    importlib.reload(ksi_to_ir)
    lib = ksi_to_ir.load_ksi_library()
    assert len(lib) >= 163, f"expected >=163 KSIs, got {len(lib)}"
    assert "KSI-IA-01" in lib
