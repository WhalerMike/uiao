"""Tests for the ADR relationship-graph guard in check_adr_references.py.

The guard fails CI when a ``supersedes`` / ``superseded_by`` / ``amends``
frontmatter edge names a non-existent ADR, names itself, or — the failure mode
it exists for — is recorded from one end only, leaving a half-edge the graph
can't be walked from.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "check_adr_references",
    Path(__file__).parent.parent / "scripts" / "check_adr_references.py",
)
guard = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(guard)


# ---------------------------------------------------------------------------
# Relationship-value parsing
# ---------------------------------------------------------------------------


def test_empty_shapes_yield_no_ids() -> None:
    assert guard.adr_ids_in(None) == set()
    assert guard.adr_ids_in("") == set()
    assert guard.adr_ids_in(" null") == set()
    assert guard.adr_ids_in(" []") == set()


def test_accepts_every_shape_the_corpus_uses() -> None:
    assert guard.adr_ids_in(" adr-066") == {"066"}
    assert guard.adr_ids_in(" adr-092-active-governance.md") == {"092"}
    assert guard.adr_ids_in(" ADR-078") == {"078"}
    # Prose entry carrying a partial-supersession scope note (adr-028's style).
    assert guard.adr_ids_in(' ["ADR-025 §D7 (federal/commercial firewall)"]') == {"025"}


def test_block_list_values_collect_every_id() -> None:
    value = "\n  - adr-063-orgpath-storage-slot-binding.md\n  - adr-078-orgpath-attribute-schema-15-facet.md"
    assert guard.adr_ids_in(value) == {"063", "078"}


def test_four_digit_numbers_are_not_adr_ids() -> None:
    # Issue references like "#1427" must never be read as ADR-1427.
    assert guard.adr_ids_in("backfill pending, issue #1427") == set()


# ---------------------------------------------------------------------------
# Frontmatter parsing
# ---------------------------------------------------------------------------


def test_extracts_frontmatter_block() -> None:
    text = "---\nadr_id: adr-001\nsupersedes: null\n---\n\n# Body\n"
    block = guard.frontmatter_block(text)
    assert block is not None
    assert "adr_id: adr-001" in block
    assert "# Body" not in block


def test_missing_or_unterminated_frontmatter_returns_none() -> None:
    assert guard.frontmatter_block("# No frontmatter\n") is None
    assert guard.frontmatter_block("---\nunterminated: true\n") is None


def test_field_text_distinguishes_absent_from_null() -> None:
    block = "\nadr_id: adr-001\nsupersedes: null\n"
    # Present-but-null yields a string; absent yields None. The presence rule
    # depends on telling these apart.
    assert guard.field_text(block, "supersedes") == " null"
    assert guard.field_text(block, "superseded_by") is None


def test_field_text_captures_block_lists_and_stops_at_next_key() -> None:
    block = "\namends:\n  - adr-063-a.md\n  - adr-078-b.md\nstatus: ACCEPTED\n"
    value = guard.field_text(block, "amends")
    assert value is not None
    assert guard.adr_ids_in(value) == {"063", "078"}
    assert "ACCEPTED" not in value


def test_field_text_ignores_a_similarly_named_key() -> None:
    block = "\nsuperseded_by: adr-028-x.md\nsupersedes: null\n"
    assert guard.adr_ids_in(guard.field_text(block, "superseded_by")) == {"028"}
    assert guard.adr_ids_in(guard.field_text(block, "supersedes")) == set()


def test_guard_imports_no_third_party_modules() -> None:
    """The workflow runs a bare setup-python with no dependency install."""
    source = (Path(__file__).parent.parent / "scripts" / "check_adr_references.py").read_text(encoding="utf-8")
    for line in source.splitlines():
        if line.startswith(("import ", "from ")) and "__future__" not in line:
            module = line.split()[1].split(".")[0]
            assert module in {"re", "sys", "pathlib"}, f"third-party import would break CI: {line!r}"


# ---------------------------------------------------------------------------
# Graph validation against the live corpus
# ---------------------------------------------------------------------------


def test_live_corpus_relationship_graph_is_clean() -> None:
    root = guard.repo_root()
    errors, _ = guard.scan_relationships(root, guard.valid_adr_ids(root))
    assert errors == [], "ADR relationship graph has unresolved or asymmetric edges:\n" + "\n".join(errors)


def test_presence_gaps_are_advisory_not_errors() -> None:
    root = guard.repo_root()
    errors, warnings = guard.scan_relationships(root, guard.valid_adr_ids(root))
    # The backfill is deliberately incomplete; gaps must not fail the gate.
    assert warnings, "expected outstanding presence warnings while backfill is pending"
    assert not any("no 'supersedes:' field" in e for e in errors)


def test_orgpath_chain_is_recorded() -> None:
    """048 <-amends- 078 <-amends- 127 -amends-> 063, the chain issue #1427 backfilled."""
    root = guard.repo_root()
    adr_dir = root / guard.ADR_DIR

    def amends_of(stem: str) -> set[str]:
        path = next(adr_dir.glob(f"{stem}-*.md"))
        block = guard.frontmatter_block(path.read_text(encoding="utf-8"))
        assert block is not None
        return guard.adr_ids_in(guard.field_text(block, "amends"))

    assert amends_of("adr-078") == {"048"}
    assert amends_of("adr-127") == {"063", "078"}
