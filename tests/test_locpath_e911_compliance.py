"""Tests for the E911 Compliance Layer — ADR-104 / UIAO_194 §Governance rule 5.

Exercises :func:`detect_e911_completeness_gaps` against synthetic
registries plus the shipped reference registry, covering the happy path
(complete dispatchable location), inheritance of the civic address from an
ancestor, and each GOV-LOCPATH-012/013/014 gap.
"""

from __future__ import annotations

import pytest

from uiao.modernization.locpath.e911_compliance import (
    DRIFT_E911_COMPLETENESS,
    ERROR_INSUFFICIENT_PRECISION,
    ERROR_NO_DISPATCHABLE_LOCATION,
    ERROR_OBLIGATION_NOT_LOCATABLE,
    detect_e911_completeness_gaps,
)
from uiao.modernization.locpath.registry import (
    LocationNode,
    LocationRegistry,
    load_location_registry,
)


def _node(loc_path: str, level: str, *, e911: dict | None = None) -> LocationNode:
    """A minimally-valid node for completeness tests (integrity isn't re-checked here)."""
    return LocationNode(
        loc_path_id=f"id-{loc_path}",
        loc_path=loc_path,
        display_name=loc_path,
        level=level,
        status="Active",
        last_updated="2026-06-13T00:00:00Z",
        source_system="test",
        e911=e911 or {},
    )


def _registry(*nodes: LocationNode) -> LocationRegistry:
    return LocationRegistry(
        registry_id="test",
        schema_version="1.0.0",
        status="reference",
        display_name="test",
        updated="2026-06-13",
        nodes=nodes,
    )


def _codes(findings) -> list[str]:
    return [f.error_code for f in findings]


# --- happy path ------------------------------------------------------------


def test_complete_dispatchable_location_no_findings():
    reg = _registry(
        _node("/USA", "Country"),
        _node("/USA/MD", "Region"),
        _node("/USA/MD/HQ", "Site", e911={"civicAddress": "100 Main St"}),
        _node(
            "/USA/MD/HQ/B1",
            "Building",
            e911={
                "dispatchableLocationRequired": True,
                "civicAddress": "100 Main St",
                "locationDescription": "Building 1",
            },
        ),
    )
    assert detect_e911_completeness_gaps(reg) == ()


def test_unflagged_nodes_are_ignored():
    # An incomplete e911 block on a node WITHOUT the obligation flag is fine.
    reg = _registry(_node("/USA/MD/HQ", "Site", e911={"floor": "2"}))
    assert detect_e911_completeness_gaps(reg) == ()


def test_civic_address_inherited_from_ancestor_satisfies_floor():
    # The Floor carries floor-level precision; the Site carries the civic
    # address. The merged effective payload is complete — no finding.
    reg = _registry(
        _node("/USA", "Country"),
        _node("/USA/MD", "Region"),
        _node("/USA/MD/HQ", "Site", e911={"civicAddress": "100 Main St"}),
        _node("/USA/MD/HQ/B1", "Building", e911={"civicAddress": "100 Main St"}),
        _node(
            "/USA/MD/HQ/B1/F2",
            "Floor",
            e911={"dispatchableLocationRequired": True, "floor": "2"},
        ),
    )
    assert detect_e911_completeness_gaps(reg) == ()


# --- gaps ------------------------------------------------------------------


def test_no_civic_address_anywhere_is_p1_012():
    reg = _registry(
        _node("/USA", "Country"),
        _node("/USA/MD", "Region"),
        _node(
            "/USA/MD/HQ",
            "Site",
            e911={"dispatchableLocationRequired": True, "locationDescription": "main gate"},
        ),
    )
    findings = detect_e911_completeness_gaps(reg)
    assert _codes(findings) == [ERROR_NO_DISPATCHABLE_LOCATION]
    assert findings[0].severity == "P1"
    assert findings[0].drift_class == DRIFT_E911_COMPLETENESS
    assert findings[0].path == "/USA/MD/HQ"


def test_civic_only_below_site_is_p2_013():
    reg = _registry(
        _node("/USA", "Country"),
        _node("/USA/MD", "Region"),
        _node("/USA/MD/HQ", "Site", e911={"civicAddress": "100 Main St"}),
        _node(
            "/USA/MD/HQ/B1",
            "Building",
            e911={"dispatchableLocationRequired": True},
        ),
    )
    findings = detect_e911_completeness_gaps(reg)
    assert _codes(findings) == [ERROR_INSUFFICIENT_PRECISION]
    assert findings[0].severity == "P2"


def test_site_with_civic_only_is_acceptable():
    # A single-structure Site may carry a complete dispatchable location
    # with civic address alone — no precision finding at Site level.
    reg = _registry(
        _node("/USA", "Country"),
        _node("/USA/MD", "Region"),
        _node(
            "/USA/MD/HQ",
            "Site",
            e911={"dispatchableLocationRequired": True, "civicAddress": "100 Main St"},
        ),
    )
    assert detect_e911_completeness_gaps(reg) == ()


def test_obligation_at_region_is_p3_014_and_skips_payload_check():
    # An obligation at a non-locatable level is a modeling fault: it is
    # reported (014) and the payload completeness check is skipped, so a
    # Region with no civicAddress does NOT also emit 012.
    reg = _registry(
        _node("/USA", "Country"),
        _node("/USA/MD", "Region", e911={"dispatchableLocationRequired": True}),
    )
    findings = detect_e911_completeness_gaps(reg)
    assert _codes(findings) == [ERROR_OBLIGATION_NOT_LOCATABLE]
    assert findings[0].severity == "P3"


def test_blank_civic_address_does_not_count_as_present():
    reg = _registry(
        _node("/USA", "Country"),
        _node("/USA/MD", "Region"),
        _node(
            "/USA/MD/HQ",
            "Site",
            e911={"dispatchableLocationRequired": True, "civicAddress": "   "},
        ),
    )
    assert _codes(detect_e911_completeness_gaps(reg)) == [ERROR_NO_DISPATCHABLE_LOCATION]


def test_findings_in_declaration_order():
    reg = _registry(
        _node("/USA", "Country"),
        _node("/USA/MD", "Region"),
        _node("/USA/MD/HQ", "Site", e911={"civicAddress": "100 Main St"}),
        _node("/USA/MD/HQ/B1", "Building", e911={"dispatchableLocationRequired": True}),
        _node(
            "/USA/MD/HQ/B2",
            "Building",
            e911={"dispatchableLocationRequired": True, "civicAddress": "200 Main St", "floor": "1"},
        ),
        _node("/USA/MD/HQ/B3", "Building", e911={"dispatchableLocationRequired": True}),
    )
    findings = detect_e911_completeness_gaps(reg)
    assert [f.path for f in findings] == ["/USA/MD/HQ/B1", "/USA/MD/HQ/B3"]


# --- shipped reference registry -------------------------------------------


def test_reference_registry_is_e911_complete():
    # The shipped worked example flags RM-210 as dispatchable-required and
    # carries a complete payload — the reference registry must stay clean.
    assert detect_e911_completeness_gaps(load_location_registry()) == ()


def test_default_loads_reference_registry():
    # Called with no argument, the pass loads the canonical reference
    # registry rather than raising.
    assert detect_e911_completeness_gaps() == ()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
