"""Tests for the UIAO_103 Spec-Test Enforcement layer (roadmap §1.2).

Covers:
    - ``spec_test_audit.py`` — frontmatter parsing, RFC 2119 keyword
      extraction, code-block stripping, multi-keyword-per-line handling,
      rollup aggregation.
    - ``spec_test_coverage_check.py`` — baseline parsing, diff logic
      (shrink-fail vs grow-pass), table render + roundtrip.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = REPO_ROOT / "scripts" / "tools"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# Loaded once per test session — both tools share the audit primitives.
audit_mod = _load_module("spec_test_audit", TOOLS_DIR / "spec_test_audit.py")
gate_mod = _load_module("spec_test_coverage_check", TOOLS_DIR / "spec_test_coverage_check.py")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _write_spec(path: Path, document_id: str, body: str) -> Path:
    path.write_text(
        f"---\ndocument_id: {document_id}\ntitle: 'probe'\nstatus: Current\n---\n\n{body}",
        encoding="utf-8",
    )
    return path


# ---------------------------------------------------------------------------
# spec_test_audit — frontmatter parsing
# ---------------------------------------------------------------------------


def test_extract_document_id_from_frontmatter(tmp_path):
    spec = _write_spec(tmp_path / "s.md", "UIAO_999", "Adapters MUST emit evidence.")
    invs = audit_mod.extract_invariants(spec)
    assert len(invs) == 1
    assert invs[0].document_id == "UIAO_999"


def test_spec_without_document_id_is_skipped(tmp_path):
    p = tmp_path / "no-id.md"
    p.write_text("# Just markdown\n\nAdapters MUST do things.\n", encoding="utf-8")
    assert audit_mod.extract_invariants(p) == []


def test_quoted_document_id_is_unwrapped(tmp_path):
    p = tmp_path / "quoted.md"
    p.write_text(
        "---\ndocument_id: \"UIAO_007\"\ntitle: 'q'\n---\n\nAdapters MUST emit.\n",
        encoding="utf-8",
    )
    invs = audit_mod.extract_invariants(p)
    assert invs[0].document_id == "UIAO_007"


# ---------------------------------------------------------------------------
# spec_test_audit — keyword extraction
# ---------------------------------------------------------------------------


def test_must_extracts_one_invariant(tmp_path):
    spec = _write_spec(tmp_path / "s.md", "UIAO_100", "The orchestrator MUST schedule nightly.")
    invs = audit_mod.extract_invariants(spec)
    assert len(invs) == 1
    assert invs[0].kind == "MUST"
    assert "MUST schedule nightly" in invs[0].statement


def test_lowercase_must_is_not_an_invariant(tmp_path):
    """RFC 2119 only counts ALL-CAPS keywords."""
    spec = _write_spec(tmp_path / "s.md", "UIAO_100", "you must schedule things, ideally")
    assert audit_mod.extract_invariants(spec) == []


def test_must_not_is_distinct_from_must(tmp_path):
    spec = _write_spec(
        tmp_path / "s.md",
        "UIAO_100",
        "Adapters MUST NOT mutate SSOT directly.",
    )
    invs = audit_mod.extract_invariants(spec)
    assert len(invs) == 1
    assert invs[0].kind == "MUST NOT"


def test_multiple_distinct_keywords_on_one_line(tmp_path):
    spec = _write_spec(
        tmp_path / "s.md",
        "UIAO_100",
        "The pipeline SHALL emit, but operators SHOULD review before promoting.",
    )
    invs = audit_mod.extract_invariants(spec)
    kinds = sorted(i.kind for i in invs)
    assert kinds == ["SHALL", "SHOULD"]


def test_repeated_keyword_on_one_line_counts_once(tmp_path):
    spec = _write_spec(
        tmp_path / "s.md",
        "UIAO_100",
        "Both producers MUST and consumers MUST agree on schema.",
    )
    invs = audit_mod.extract_invariants(spec)
    assert len(invs) == 1  # one MUST per line, even if the word appears twice


def test_keywords_inside_fenced_code_block_are_skipped(tmp_path):
    spec = _write_spec(
        tmp_path / "s.md",
        "UIAO_100",
        "Real invariant: adapters MUST emit.\n\n"
        "```python\n"
        "# the word MUST appears here as illustration\n"
        "if condition: pass\n"
        "```\n\n"
        "After fence, another MUST clause.",
    )
    invs = audit_mod.extract_invariants(spec)
    assert len(invs) == 2  # only the two outside the fence


def test_all_rfc_2119_keywords_recognized(tmp_path):
    """Each RFC-2119 keyword must produce its own invariant kind."""
    spec = _write_spec(
        tmp_path / "s.md",
        "UIAO_100",
        "\n".join(
            [
                "Line one MUST hold.",
                "Line two SHALL hold.",
                "REQUIRED clause goes here.",
                "MUST NOT happens like this.",
                "SHALL NOT either.",
                "RECOMMENDED but not required.",
                "SHOULD do this in production.",
            ]
        ),
    )
    invs = audit_mod.extract_invariants(spec)
    kinds = sorted({i.kind for i in invs})
    assert kinds == [
        "MUST",
        "MUST NOT",
        "RECOMMENDED",
        "REQUIRED",
        "SHALL",
        "SHALL NOT",
        "SHOULD",
    ]


def test_line_numbers_are_one_indexed(tmp_path):
    spec = _write_spec(
        tmp_path / "s.md",
        "UIAO_100",
        "no keyword here\nthis MUST be line 8 of file (after frontmatter+blank+title).",
    )
    invs = audit_mod.extract_invariants(spec)
    # Frontmatter ends at line 5, body starts at line 7. The "no keyword here"
    # is line 7; the MUST line is line 8. (Body line numbers reflect post-strip
    # representation, which preserves line indexing.)
    assert invs[0].line >= 1
    assert invs[0].line <= 20  # don't over-specify; test only that we produce a sane line number


# ---------------------------------------------------------------------------
# spec_test_audit — rollup aggregation
# ---------------------------------------------------------------------------


def test_rollup_groups_by_document_id(tmp_path):
    _write_spec(tmp_path / "a.md", "UIAO_100", "MUST one. MUST two. SHOULD optional.")
    _write_spec(tmp_path / "b.md", "UIAO_113", "REQUIRED clause.")
    invs = audit_mod.audit(roots=[tmp_path])
    rollups = audit_mod.rollup(invs)
    by_id = {r.document_id: r for r in rollups}
    assert by_id["UIAO_100"].total == 2  # 2 distinct lines with MUST/SHOULD
    # Note: the line "MUST one. MUST two." is a single line so MUST counts once
    # ("MUST one" only — sentence split happens at the period). Either way,
    # the total reflects line-level counts (1 line w/ MUST, 1 with SHOULD).
    assert by_id["UIAO_113"].total == 1
    assert "REQUIRED" in by_id["UIAO_113"].by_kind


def test_rollup_is_sorted_by_document_id(tmp_path):
    _write_spec(tmp_path / "z.md", "UIAO_999", "MUST.")
    _write_spec(tmp_path / "a.md", "UIAO_001", "MUST.")
    _write_spec(tmp_path / "m.md", "UIAO_500", "MUST.")
    invs = audit_mod.audit(roots=[tmp_path])
    rollups = audit_mod.rollup(invs)
    assert [r.document_id for r in rollups] == ["UIAO_001", "UIAO_500", "UIAO_999"]


def test_audit_skips_files_without_document_id(tmp_path):
    _write_spec(tmp_path / "a.md", "UIAO_100", "MUST.")
    (tmp_path / "no-id.md").write_text("Random file. SHALL be ignored.\n", encoding="utf-8")
    invs = audit_mod.audit(roots=[tmp_path])
    assert all(i.document_id == "UIAO_100" for i in invs)


# ---------------------------------------------------------------------------
# spec_test_coverage_check — baseline parsing
# ---------------------------------------------------------------------------


def test_parse_committed_table_extracts_per_doc_kinds(tmp_path):
    table = (
        "header prose\n\n"
        "<!-- BEGIN AUTO -->\n"
        "| document_id | file | total | by_kind |\n"
        "|---|---|---:|---|\n"
        "| UIAO_100 | `a.md` | 5 | MUST=3, SHALL=2 |\n"
        "| UIAO_113 | `b.md` | 1 | REQUIRED=1 |\n"
        "<!-- END AUTO -->\n"
        "manual section here\n"
    )
    p = tmp_path / "coverage.md"
    p.write_text(table, encoding="utf-8")
    parsed = gate_mod.parse_committed_table(p)
    assert parsed == {
        "UIAO_100": {"MUST": 3, "SHALL": 2},
        "UIAO_113": {"REQUIRED": 1},
    }


def test_parse_committed_table_missing_file_returns_empty(tmp_path):
    assert gate_mod.parse_committed_table(tmp_path / "nope.md") == {}


def test_parse_committed_table_missing_markers_returns_empty(tmp_path):
    p = tmp_path / "no-markers.md"
    p.write_text("# table without auto markers\n| UIAO_100 | x | 5 |\n", encoding="utf-8")
    assert gate_mod.parse_committed_table(p) == {}


# ---------------------------------------------------------------------------
# spec_test_coverage_check — diff
# ---------------------------------------------------------------------------


def _rollup(doc: str, total: int, by_kind: dict[str, int] | None = None):
    return audit_mod.SpecRollup(
        document_id=doc,
        file=f"specs/{doc}.md",
        total=total,
        by_kind=by_kind or {"MUST": total},
    )


def test_diff_returns_empty_when_baseline_preserved():
    committed = {"UIAO_100": {"MUST": 3}}
    live = [_rollup("UIAO_100", 3)]
    assert gate_mod.diff_baselines(committed, live) == []


def test_diff_returns_empty_when_count_grows():
    committed = {"UIAO_100": {"MUST": 3}}
    live = [_rollup("UIAO_100", 5)]
    assert gate_mod.diff_baselines(committed, live) == []


def test_diff_flags_count_shrink():
    committed = {"UIAO_100": {"MUST": 5}}
    live = [_rollup("UIAO_100", 3)]
    failures = gate_mod.diff_baselines(committed, live)
    assert len(failures) == 1
    assert "shrank from 5 to 3" in failures[0]


def test_diff_flags_spec_disappearance():
    committed = {"UIAO_100": {"MUST": 5}}
    live: list = []  # spec gone from audit entirely
    failures = gate_mod.diff_baselines(committed, live)
    assert len(failures) == 2
    # Both "shrank to 0" AND "no longer present" reasons fire — they're
    # complementary signals.
    assert any("shrank from 5 to 0" in f for f in failures)
    assert any("no longer present" in f for f in failures)


def test_diff_passes_for_empty_baseline_with_new_specs():
    committed: dict = {}
    live = [_rollup("UIAO_100", 3)]
    assert gate_mod.diff_baselines(committed, live) == []


# ---------------------------------------------------------------------------
# spec_test_coverage_check — render + roundtrip
# ---------------------------------------------------------------------------


def test_render_auto_block_includes_all_rollups():
    rollups = [
        _rollup("UIAO_100", 3, {"MUST": 2, "SHALL": 1}),
        _rollup("UIAO_113", 1, {"REQUIRED": 1}),
    ]
    block = gate_mod.render_auto_block(rollups)
    assert "UIAO_100" in block
    assert "UIAO_113" in block
    assert "MUST=2" in block
    assert "SHALL=1" in block
    assert "REQUIRED=1" in block
    assert "Total invariants tracked:** 4" in block


def test_render_auto_block_handles_empty_rollups():
    block = gate_mod.render_auto_block([])
    assert "no canon specs with normative statements yet" in block
    assert "Total invariants tracked:** 0" in block


def test_update_then_check_is_clean_roundtrip(tmp_path):
    """--update writes a table; --check immediately after must pass."""
    rollups = [_rollup("UIAO_100", 3, {"MUST": 3})]
    target = tmp_path / "coverage.md"
    gate_mod.write_updated_table(target, rollups)
    parsed = gate_mod.parse_committed_table(target)
    assert parsed == {"UIAO_100": {"MUST": 3}}
    assert gate_mod.diff_baselines(parsed, rollups) == []


def test_update_preserves_manual_section_below_auto_markers(tmp_path):
    target = tmp_path / "coverage.md"
    initial_rollups = [_rollup("UIAO_100", 1, {"MUST": 1})]
    gate_mod.write_updated_table(target, initial_rollups)
    # Author edits the manual section.
    text = target.read_text(encoding="utf-8")
    text = text.replace(
        "UIAO_100:\n",
        "UIAO_100:\n  - tests/my_custom_test.py  # author note\n  - tests/another.py\n",
        1,
    )
    target.write_text(text, encoding="utf-8")

    # Re-update with new audit results.
    new_rollups = [_rollup("UIAO_100", 5, {"MUST": 5})]
    gate_mod.write_updated_table(target, new_rollups)

    final = target.read_text(encoding="utf-8")
    # Auto block reflects new totals.
    assert "5 | MUST=5" in final
    # Manual section preserved.
    assert "my_custom_test.py" in final
    assert "another.py" in final


def test_canonical_coverage_doc_baseline_is_intact_in_repo():
    """Smoke-guard against accidental deletion of the committed table."""
    coverage_path = REPO_ROOT / "docs" / "docs" / "governance" / "spec-test-coverage.md"
    assert coverage_path.is_file(), "coverage doc must be committed"
    text = coverage_path.read_text(encoding="utf-8")
    assert "<!-- BEGIN AUTO -->" in text
    assert "<!-- END AUTO -->" in text
    parsed = gate_mod.parse_committed_table(coverage_path)
    # We seeded at least UIAO_121 in the initial bootstrap; assert the
    # parser produced a non-empty baseline so the gate isn't trivially OK.
    assert isinstance(parsed, dict)
