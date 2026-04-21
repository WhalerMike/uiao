"""Smoke tests for scripts/tools/docs_leak_check.py.

Exercises each rule (R1–R3) against a synthetic docs tree inside a
tmp_path, plus the backtick-allowlist convention, plus the
false-positive exclusions (Python package `src/uiao/evidence/*`,
unrelated `evidence/latest.json` CLI paths).

The module under test uses a module-level `DOCS_ROOT = pathlib.Path("docs")`
so we monkeypatch it to point at the temp tree for each test.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys
import textwrap

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SCANNER_PATH = REPO_ROOT / "scripts" / "tools" / "docs_leak_check.py"


def _load_scanner_module():
    spec = importlib.util.spec_from_file_location("docs_leak_check_mod", SCANNER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["docs_leak_check_mod"] = module
    spec.loader.exec_module(module)
    return module


scanner = _load_scanner_module()


def _run(tmp_docs: pathlib.Path, monkeypatch) -> int:
    monkeypatch.setattr(scanner, "DOCS_ROOT", tmp_docs)
    return scanner.main()


def test_clean_tree_passes(tmp_path, monkeypatch):
    docs = tmp_path / "docs"
    (docs / "sub").mkdir(parents=True)
    (docs / "sub" / "page.md").write_text(
        "# hi\n\nreal code: `evidence/conformance/x` is fine inside backticks.\n",
        encoding="utf-8",
    )
    assert _run(docs, monkeypatch) == 0


def test_r1_flags_evidence_subdir(tmp_path, monkeypatch):
    docs = tmp_path / "docs"
    (docs / "evidence").mkdir(parents=True)
    (docs / "evidence" / "leak.md").write_text("secret", encoding="utf-8")
    assert _run(docs, monkeypatch) == 1


def test_r2_flags_bare_evidence_conformance_reference(tmp_path, monkeypatch):
    docs = tmp_path / "docs"
    docs.mkdir(parents=True)
    (docs / "page.md").write_text(
        "This leaks evidence/conformance/scubagear/run-1/findings.json bare.\n",
        encoding="utf-8",
    )
    assert _run(docs, monkeypatch) == 1


def test_r2_permits_backticked_reference(tmp_path, monkeypatch):
    docs = tmp_path / "docs"
    docs.mkdir(parents=True)
    (docs / "page.md").write_text(
        "This documents `evidence/conformance/scubagear/` correctly.\n",
        encoding="utf-8",
    )
    assert _run(docs, monkeypatch) == 0


def test_r2_permits_fenced_block_reference(tmp_path, monkeypatch):
    docs = tmp_path / "docs"
    docs.mkdir(parents=True)
    (docs / "page.md").write_text(
        textwrap.dedent(
            """
            Here is a fenced block:

            ```yaml
            outputs:
              - path: evidence/conformance/scubagear/run-1/findings.json
            ```
            """
        ).strip(),
        encoding="utf-8",
    )
    assert _run(docs, monkeypatch) == 0


def test_r2_ignores_python_package_paths(tmp_path, monkeypatch):
    docs = tmp_path / "docs"
    docs.mkdir(parents=True)
    (docs / "page.md").write_text(
        "The module src/uiao/evidence/builder.py builds bundles.\n",
        encoding="utf-8",
    )
    assert _run(docs, monkeypatch) == 0


def test_r2_ignores_generic_evidence_paths(tmp_path, monkeypatch):
    docs = tmp_path / "docs"
    docs.mkdir(parents=True)
    (docs / "page.md").write_text(
        "Run `uiao evidence verify --bundle evidence/latest.json` for a smoke test.\n",
        encoding="utf-8",
    )
    # `evidence/latest.json` is outside the sensitive-subtree list
    # (conformance, conmon, oscal, sar, ssp, poam, findings). Clean.
    assert _run(docs, monkeypatch) == 0


def test_r3_flags_committed_site_output(tmp_path, monkeypatch):
    docs = tmp_path / "docs"
    (docs / "_site").mkdir(parents=True)
    (docs / "_site" / "index.html").write_text("<html></html>", encoding="utf-8")
    assert _run(docs, monkeypatch) == 1


def test_multiple_rules_all_reported(tmp_path, monkeypatch, capsys):
    docs = tmp_path / "docs"
    (docs / "evidence").mkdir(parents=True)  # R1
    (docs / "evidence" / "leak.md").write_text("x", encoding="utf-8")
    (docs / "page.md").write_text(
        "References evidence/sar/real-sar.json bare.\n",  # R2
        encoding="utf-8",
    )
    (docs / "_site").mkdir()
    (docs / "_site" / "leak.html").write_text("x", encoding="utf-8")  # R3
    rc = _run(docs, monkeypatch)
    err = capsys.readouterr().err
    assert rc == 1
    assert "R1:" in err
    assert "R2:" in err
    assert "R3:" in err


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
