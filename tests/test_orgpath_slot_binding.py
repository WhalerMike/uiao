"""Tests for the OrgPath slot-binding guard (ADR-078 / ADR-121 / ADR-127).

The guard fails when prose binds a non-derived slot to the OrgPath *value* —
the retired Model A/B shape (``extensionAttribute1 = "ORG-FIN"``) that ADR-078
replaced with facets and ADR-127 moved to ``extensionAttribute15``.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "check_orgpath_slot_binding",
    Path(__file__).parent.parent / "scripts" / "check_orgpath_slot_binding.py",
)
lint = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(lint)

PATH_SLOT = "15"


def scan(line: str) -> list[str]:
    return lint.scan_text(line, "sample.md", PATH_SLOT)


# ---------------------------------------------------------------------------
# Retired bindings are caught
# ---------------------------------------------------------------------------


def test_flags_composite_path_literal_bound_to_a_facet_slot() -> None:
    assert scan('(user.extensionAttribute1 -eq "ORG-FIN")')
    assert scan("| extensionAttribute1 | OrgPath canonical address | `CORP/US/EAST/BALTIMORE/IT` |")


def test_flags_orgpath_bound_as_a_stored_value() -> None:
    assert scan("Stage 3: SCIM payload with extensionAttribute1 = OrgPath")
    assert scan("`extensionAttribute1` (OrgPath).")
    assert scan("For each user, write the OrgPath value to extensionAttribute1.")


# ---------------------------------------------------------------------------
# Correct and out-of-scope content is not flagged
# ---------------------------------------------------------------------------


def test_derived_slot_is_always_clean() -> None:
    assert not scan('(user.extensionAttribute15 -startsWith "Department=Finance|")')
    assert not scan("write the derived OrgPath to extensionAttribute15")


def test_facet_slots_without_an_orgpath_binding_are_clean() -> None:
    # extensionAttribute1 IS the region facet — naming it is correct, not drift.
    assert not scan("extensionAttribute1:    NCR          # region")
    assert not scan("| extensionAttribute2 | department | Finance |")


def test_ranges_describe_the_family_and_are_out_of_scope() -> None:
    assert not scan("facets on extensionAttribute1-14 carry the governance layer")
    assert not scan("OrgPath facets spread across `extensionAttribute1`–`10` (5 reserved)")
    assert not scan("stamp the OrgPath facets (`extensionAttribute1`-`10`)")


def test_bare_programme_mentions_are_not_bindings() -> None:
    # "OrgPath" is the name of the whole system; only an asserted binding counts.
    assert not scan("OrgPath drives dynamic group membership and AU scoping.")
    assert not scan("The OrgPath codebook is versioned in Git.")


# ---------------------------------------------------------------------------
# Exemptions
# ---------------------------------------------------------------------------


def test_line_marker_exempts_one_line() -> None:
    line = 'extensionAttribute1 = "ORG-FIN"  <!-- orgpath-slot-allow: retired form, shown deliberately -->'
    assert not scan(line)


def test_file_marker_exempts_the_whole_document() -> None:
    text = "<!-- orgpath-slot-allow-file: historical -->\n" + '(user.extensionAttribute1 -eq "ORG-FIN")\n'
    assert not lint.scan_text(text, "historical.md", PATH_SLOT)


# ---------------------------------------------------------------------------
# The codebook is the SSOT, not a hardcoded constant
# ---------------------------------------------------------------------------


def test_derived_slot_is_read_from_the_codebook() -> None:
    assert lint.org_path_slot(lint.repo_root()) == "15"


def test_facet_slots_come_from_the_codebook() -> None:
    slots = lint.facet_slots(lint.repo_root())
    assert slots["region"] == "1"
    assert slots["org_path"] == "15"


# ---------------------------------------------------------------------------
# Live corpus
# ---------------------------------------------------------------------------


def test_canon_is_clean_under_strict() -> None:
    """Canon is enforced with --strict in CI; docs/ backlog is tracked separately."""
    assert lint.main(["--strict", "--path", "src/uiao/canon"]) == 0


def test_guard_imports_no_third_party_modules() -> None:
    """The workflow runs a bare setup-python with no dependency install.

    First-party siblings under ``scripts/`` are fine — they ship in the
    checkout. Only a genuinely third-party import would break CI.
    """
    stdlib = {"argparse", "re", "sys", "pathlib"}
    first_party = {"_console"}
    source = (Path(__file__).parent.parent / "scripts" / "check_orgpath_slot_binding.py").read_text(encoding="utf-8")
    for line in source.splitlines():
        if line.startswith(("import ", "from ")) and "__future__" not in line:
            module = line.split()[1].split(".")[0]
            assert module in stdlib | first_party, f"third-party import would break CI: {line!r}"
