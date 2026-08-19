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
    assert guard.adr_ids_in([]) == set()
    assert guard.adr_ids_in(123) == set()


def test_accepts_every_shape_the_corpus_uses() -> None:
    assert guard.adr_ids_in("adr-066") == {"066"}
    assert guard.adr_ids_in("adr-092-active-governance.md") == {"092"}
    assert guard.adr_ids_in("ADR-078") == {"078"}
    # Prose entry carrying a partial-supersession scope note (adr-028's style).
    assert guard.adr_ids_in(["ADR-025 §D7 (federal/commercial firewall)"]) == {"025"}


def test_list_values_collect_every_id() -> None:
    value = [
        "adr-063-orgpath-storage-slot-binding.md",
        "adr-078-orgpath-attribute-schema-15-facet.md",
    ]
    assert guard.adr_ids_in(value) == {"063", "078"}


def test_four_digit_numbers_are_not_adr_ids() -> None:
    # Issue references like "#1427" must never be read as ADR-1427.
    assert guard.adr_ids_in("backfill pending, issue #1427") == set()


# ---------------------------------------------------------------------------
# Frontmatter parsing
# ---------------------------------------------------------------------------


def test_parses_frontmatter_block() -> None:
    text = "---\nadr_id: adr-001\nsupersedes: null\n---\n\n# Body\n"
    assert guard.parse_frontmatter(text) == {"adr_id": "adr-001", "supersedes": None}


def test_missing_or_malformed_frontmatter_returns_none() -> None:
    assert guard.parse_frontmatter("# No frontmatter\n") is None
    assert guard.parse_frontmatter("---\nunterminated: true\n") is None
    assert guard.parse_frontmatter("---\n- just\n- a list\n---\n") is None


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
        frontmatter = guard.parse_frontmatter(path.read_text(encoding="utf-8"))
        assert frontmatter is not None
        return guard.adr_ids_in(frontmatter.get("amends"))

    assert amends_of("adr-078") == {"048"}
    assert amends_of("adr-127") == {"063", "078"}
