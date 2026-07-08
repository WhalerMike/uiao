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


def test_default_codebook_has_eleven_named_facets_plus_four_reserved() -> None:
    # 10 governance facets + the ADR-127 derived org_path on slot 15;
    # slots 11-14 stay reserved for tenant extension.
    codebook = load_codebook()
    named = [f for f in codebook.facets.values() if f.kind != "reserved"]
    reserved = [f for f in codebook.facets.values() if f.kind == "reserved"]
    assert len(named) == 11
    assert len(reserved) == 4


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


# ---------------------------------------------------------------------------
# Hybrid-C+Path (ADR-127): derived OrgPath on extensionAttribute15
# ---------------------------------------------------------------------------


def test_hybrid_block_declares_inheritance_layer() -> None:
    codebook = load_codebook()
    assert codebook.hybrid is not None
    assert codebook.hybrid["name"] == "Hybrid-C+Path"
    assert codebook.hybrid["status"] == "ACCEPTED"
    layer = codebook.hybrid["inheritance_layer"]
    assert layer["facet"] == "org_path"
    assert layer["attribute"] == "extensionAttribute15"
    assert layer["derived_from"] == ["region", "department", "division"]
    assert layer["delimiter"] == "|"
    assert layer["trailing_delimiter"] == "always present"


def test_org_path_facet_binds_slot_fifteen() -> None:
    codebook = load_codebook()
    org_path = codebook.facet("org_path")
    assert org_path.attribute == "extensionAttribute15"
    assert org_path.kind == "typed"
    assert org_path.projected is True


def test_org_path_pattern_requires_trailing_delimiter() -> None:
    codebook = load_codebook()
    org_path = codebook.facet("org_path")
    assert org_path.is_active("Region=NCR|Department=IT|Division=CyberOps|")
    assert org_path.is_active("Region=NCR|")
    # Trailing delimiter is always present — an unterminated path is drift.
    assert not org_path.is_active("Region=NCR|Department=IT|Division=CyberOps")
    assert not org_path.is_active("Region=NCR")
    # Empty is allowed: the derived path is absent until facets populate.
    assert org_path.is_active("")


def test_hybrid_rejects_unknown_derived_from_facet(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        _MIN_HEADER
        + "  org_path:\n"
        + "    attribute: extensionAttribute15\n"
        + "    description: Derived path\n"
        + "    kind: typed\n"
        + "    value_type: string\n"
        + "hybrid:\n"
        + "  name: Hybrid-C+Path\n"
        + '  status: ACCEPTED\n'
        + '  version: "2026-07-07"\n'
        + "  governance_layer:\n"
        + '    attributes: "extensionAttribute1-14"\n'
        + "    description: Facets\n"
        + "  inheritance_layer:\n"
        + "    facet: org_path\n"
        + "    attribute: extensionAttribute15\n"
        + "    derived_from: [region, not_a_facet]\n"
        + '    delimiter: "|"\n'
        + '    trailing_delimiter: "always present"\n'
    )
    with pytest.raises(CodebookValidationError, match="not_a_facet"):
        load_codebook(bad)


def test_hybrid_rejects_attribute_mismatch(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        _MIN_HEADER
        + "  org_path:\n"
        + "    attribute: extensionAttribute15\n"
        + "    description: Derived path\n"
        + "    kind: typed\n"
        + "    value_type: string\n"
        + "hybrid:\n"
        + "  name: Hybrid-C+Path\n"
        + '  status: ACCEPTED\n'
        + '  version: "2026-07-07"\n'
        + "  governance_layer:\n"
        + '    attributes: "extensionAttribute1-14"\n'
        + "    description: Facets\n"
        + "  inheritance_layer:\n"
        + "    facet: org_path\n"
        + "    attribute: extensionAttribute14\n"
        + "    derived_from: [region]\n"
        + '    delimiter: "|"\n'
        + '    trailing_delimiter: "always present"\n'
    )
    with pytest.raises(CodebookValidationError, match="does not match"):
        load_codebook(bad)


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
