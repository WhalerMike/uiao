"""Tests for the OrgPath codebook loader — Model C (ADR-078, UIAO_151)."""

from __future__ import annotations

from pathlib import Path

import pytest

from uiao.modernization.orgtree import (
    Codebook,
    CodebookValidationError,
    Facet,
    load_codebook,
)


# ---------------------------------------------------------------------------
# Default codebook
# ---------------------------------------------------------------------------


def test_default_codebook_loads_and_validates() -> None:
    codebook = load_codebook()
    assert isinstance(codebook, Codebook)
    assert codebook.document_id == "UIAO_151"
    assert codebook.model == "C"
    assert codebook.schema_version.startswith("2.")
    assert codebook.adoption_tier_min == 3


def test_default_codebook_has_ten_named_facets_plus_five_reserved() -> None:
    codebook = load_codebook()
    named = [f for f in codebook.facets.values() if f.kind != "reserved"]
    reserved = [f for f in codebook.facets.values() if f.kind == "reserved"]
    assert len(named) == 10
    assert len(reserved) == 5


def test_canonical_facet_slot_assignments() -> None:
    """Per ADR-078 §Canonical attribute assignments."""
    codebook = load_codebook()
    expected = {
        "region": "extensionAttribute1",
        "department": "extensionAttribute2",
        "division": "extensionAttribute3",
        "role": "extensionAttribute4",
        "cost_center": "extensionAttribute5",
        "classification": "extensionAttribute6",
        "hire_date": "extensionAttribute7",
        "term_date": "extensionAttribute8",
        "clearance_level": "extensionAttribute9",
        "account_type": "extensionAttribute10",
    }
    for name, slot in expected.items():
        facet = codebook.facet(name)
        assert facet.attribute == slot, f"facet {name} should bind {slot}"


def test_facet_lookup_by_attribute() -> None:
    codebook = load_codebook()
    region = codebook.facet_by_attribute("extensionAttribute1")
    assert region is not None
    assert region.name == "region"


def test_facet_lookup_by_attribute_returns_none_when_unknown() -> None:
    codebook = load_codebook()
    assert codebook.facet_by_attribute("extensionAttribute99") is None


# ---------------------------------------------------------------------------
# Per-facet API
# ---------------------------------------------------------------------------


def test_enumerated_facet_is_active_for_known_value() -> None:
    codebook = load_codebook()
    region = codebook.facet("region")
    assert region.is_active("NCR")
    assert region.is_active("WESTUS")


def test_enumerated_facet_is_inactive_for_unknown_value() -> None:
    codebook = load_codebook()
    region = codebook.facet("region")
    assert not region.is_active("ATLANTIS")


def test_typed_facet_validates_value_pattern() -> None:
    codebook = load_codebook()
    hire_date = codebook.facet("hire_date")
    assert hire_date.kind == "typed"
    assert hire_date.is_active("2024-01-15")
    assert not hire_date.is_active("not-a-date")


def test_typed_facet_allow_empty_for_term_date() -> None:
    """TermDate is empty for active employees per ADR-078."""
    codebook = load_codebook()
    term_date = codebook.facet("term_date")
    assert term_date.allow_empty is True
    assert term_date.is_active("")
    assert term_date.is_active("2030-12-31")
    assert not term_date.is_active("not-a-date")


def test_reserved_facet_rejects_all_values() -> None:
    codebook = load_codebook()
    reserved = codebook.facet("reserved_11")
    assert reserved.kind == "reserved"
    assert not reserved.is_active("anything")
    assert not reserved.is_active("")


def test_facet_unknown_raises_keyerror() -> None:
    codebook = load_codebook()
    with pytest.raises(KeyError, match="not declared"):
        codebook.facet("not_a_facet")


# ---------------------------------------------------------------------------
# Integrity validation
# ---------------------------------------------------------------------------


_MIN_HEADER = """\
schema_version: "2.0.0"
document_id: UIAO_151
parent_canon: UIAO_007
model: "C"
adoption_tier_min: 3
facets:
  region:
    attribute: extensionAttribute1
    description: Geographic region
    kind: enumerated
    enumeration:
      - { value: NCR, description: National Capital Region }
"""


def test_rejects_slot_collision(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    # second_facet (extra facet) sits at 2-space indent — sibling of `region` inside `facets:`
    bad.write_text(
        _MIN_HEADER
        + "  second_facet:\n"
        + "    attribute: extensionAttribute1\n"
        + "    description: Collision\n"
        + "    kind: enumerated\n"
        + "    enumeration:\n"
        + "      - { value: X, description: collision value }\n"
        + "deprecated: {}\n"
    )
    with pytest.raises(CodebookValidationError, match="both bind"):
        load_codebook(bad)


def test_rejects_deprecated_replacement_not_in_enumeration(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text(_MIN_HEADER + "deprecated:\n" + "  region:\n" + "    - { value: OLDREGION, replaced_by: NOPE }\n")
    with pytest.raises(CodebookValidationError, match="not an active enumeration value"):
        load_codebook(bad)


def test_rejects_deprecated_for_non_enumerated_facet(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        _MIN_HEADER
        + "  hire_date:\n"
        + "    attribute: extensionAttribute7\n"
        + "    description: Hire date\n"
        + "    kind: typed\n"
        + "    value_type: date\n"
        + "deprecated:\n"
        + "  hire_date:\n"
        + '    - { value: "2020-01-01", replaced_by: "2024-01-01" }\n'
    )
    with pytest.raises(CodebookValidationError, match="non-enumerated"):
        load_codebook(bad)


def test_deprecated_value_round_trip_in_enumerated_facet(tmp_path: Path) -> None:
    good = tmp_path / "good.yaml"
    good.write_text(
        _MIN_HEADER
        + "  department:\n"
        + "    attribute: extensionAttribute2\n"
        + "    description: Department\n"
        + "    kind: enumerated\n"
        + "    enumeration:\n"
        + "      - { value: IT, description: Information Technology }\n"
        + "      - { value: Engineering, description: Engineering }\n"
        + "deprecated:\n"
        + "  department:\n"
        + '    - { value: ITSecurity, replaced_by: IT, reason: "Consolidated" }\n'
    )
    codebook = load_codebook(good)
    dept = codebook.facet("department")
    assert dept.is_deprecated("ITSecurity")
    assert dept.replacement_for("ITSecurity") == "IT"
    assert dept.is_valid_value("ITSecurity")  # deprecated values still recognized
    assert dept.is_valid_value("IT")  # active value
    assert not dept.is_valid_value("NOPE")


# ---------------------------------------------------------------------------
# Sanity: typed facets are well-formed
# ---------------------------------------------------------------------------


def test_typed_facets_declare_value_type() -> None:
    codebook = load_codebook()
    for facet in codebook.facets.values():
        if facet.kind == "typed":
            assert facet.value_type is not None, f"{facet.name} missing value_type"


def test_facet_dataclass_is_frozen() -> None:
    codebook = load_codebook()
    region = codebook.facet("region")
    assert isinstance(region, Facet)
    with pytest.raises((AttributeError, Exception)):
        region.name = "renamed"  # type: ignore[misc]
