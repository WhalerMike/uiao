"""Tests for the LocPath location-registry loader (ADR-102 §D6 / UIAO_194).

Covers: the shipped reference registry loads and validates; the prefix-
matching lookup contract (UIAO_194 §Path syntax); and every integrity
rule the loader enforces beyond JSON Schema (level/depth consistency,
case-insensitive path uniqueness, locPathId uniqueness + UUID
parseability, parent existence, ISO-8601 timestamps).
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest
import yaml

from uiao.modernization.locpath import (
    LEVEL_DEPTH,
    LEVELS,
    LocationRegistryValidationError,
    load_location_registry,
    load_location_registry_from_path,
)

REFERENCE_YAML = Path(__file__).resolve().parents[1] / "src/uiao/canon/data/locpath/location-registry.yaml"


def _reference_doc() -> dict[str, Any]:
    doc = yaml.safe_load(REFERENCE_YAML.read_text(encoding="utf-8"))
    assert isinstance(doc, dict)
    return doc


def _write(tmp_path: Path, doc: dict[str, Any]) -> Path:
    out = tmp_path / "registry.yaml"
    out.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    return out


# ---------------------------------------------------------------------------
# Reference registry — the executable UIAO_194 worked example
# ---------------------------------------------------------------------------


def test_levels_and_depths_are_canonical() -> None:
    assert LEVELS == ("Country", "Region", "Site", "Building", "Floor", "Space")
    assert LEVEL_DEPTH["Country"] == 1
    assert LEVEL_DEPTH["Space"] == 6


def test_reference_registry_loads_from_packaged_canon() -> None:
    registry = load_location_registry()
    assert registry.registry_id == "reference"
    assert registry.status == "reference"
    assert len(registry.nodes) == 6
    # One node per hierarchy level — the worked example spans the full chain.
    assert tuple(n.level for n in registry.nodes) == LEVELS


def test_reference_site_carries_classification_blocks() -> None:
    registry = load_location_registry()
    (site,) = registry.sites()
    assert site.loc_path == "/USA/MD/ANNAPOLIS-HQ"
    assert site.network["diaApproved"] is True
    assert site.network["ticCapabilityTier"] == "Tier-1"
    assert site.boundaries["telemetryBoundary"] == "GCCAllowed"


def test_reference_space_carries_dispatchable_location() -> None:
    registry = load_location_registry()
    room = registry.node_for("/USA/MD/ANNAPOLIS-HQ/BLDG-3/FL-2/RM-210")
    assert room is not None
    assert room.level == "Space"
    assert room.e911["civicAddress"] == "100 Main Street, Annapolis, MD 21401"
    assert room.e911["floor"] == "2"
    assert room.e911["room"] == "RM-210"


# ---------------------------------------------------------------------------
# Lookup contract — case-insensitive exact + prefix matching
# ---------------------------------------------------------------------------


def test_node_for_is_case_insensitive() -> None:
    registry = load_location_registry()
    node = registry.node_for("/usa/md/annapolis-hq")
    assert node is not None
    assert node.loc_path == "/USA/MD/ANNAPOLIS-HQ"  # canonical casing preserved


def test_nodes_under_covers_node_and_descendants() -> None:
    registry = load_location_registry()
    covered = registry.nodes_under("/USA/MD/ANNAPOLIS-HQ")
    assert [n.level for n in covered] == ["Site", "Building", "Floor", "Space"]
    # Prefix matching is segment-aware: /USA does not also match /USAX.
    assert registry.nodes_under("/USA/MD/ANNAPOLIS") == ()


def test_ancestors_of_returns_outermost_first() -> None:
    registry = load_location_registry()
    ancestors = registry.ancestors_of("/USA/MD/ANNAPOLIS-HQ/BLDG-3/FL-2/RM-210")
    assert [a.level for a in ancestors] == ["Country", "Region", "Site", "Building", "Floor"]


def test_parent_path_property() -> None:
    registry = load_location_registry()
    country = registry.node_for("/USA")
    building = registry.node_for("/USA/MD/ANNAPOLIS-HQ/BLDG-3")
    assert country is not None and country.parent_path is None
    assert building is not None and building.parent_path == "/USA/MD/ANNAPOLIS-HQ"


# ---------------------------------------------------------------------------
# Integrity rules beyond JSON Schema
# ---------------------------------------------------------------------------


def test_level_depth_mismatch_rejected(tmp_path: Path) -> None:
    doc = _reference_doc()
    doc["nodes"][2]["level"] = "Building"  # Site path with Building level
    with pytest.raises(LocationRegistryValidationError, match="declares level 'Building'"):
        load_location_registry_from_path(_write(tmp_path, doc))


def test_case_insensitive_path_collision_rejected(tmp_path: Path) -> None:
    doc = _reference_doc()
    dupe = copy.deepcopy(doc["nodes"][1])
    dupe["locPath"] = "/usa/md"
    dupe["locPathId"] = "9b1c5a40-22e4-4a31-8b51-0000000000ff"
    doc["nodes"].append(dupe)
    with pytest.raises(LocationRegistryValidationError, match="collides"):
        load_location_registry_from_path(_write(tmp_path, doc))


def test_duplicate_loc_path_id_rejected(tmp_path: Path) -> None:
    doc = _reference_doc()
    doc["nodes"][1]["locPathId"] = doc["nodes"][0]["locPathId"]
    with pytest.raises(LocationRegistryValidationError, match="duplicate locPathId"):
        load_location_registry_from_path(_write(tmp_path, doc))


def test_non_uuid_loc_path_id_rejected(tmp_path: Path) -> None:
    doc = _reference_doc()
    doc["nodes"][0]["locPathId"] = "not-a-uuid"
    with pytest.raises(LocationRegistryValidationError, match="not a UUID"):
        load_location_registry_from_path(_write(tmp_path, doc))


def test_missing_parent_rejected(tmp_path: Path) -> None:
    doc = _reference_doc()
    del doc["nodes"][3]  # remove BLDG-3; FL-2 is now an orphan
    with pytest.raises(LocationRegistryValidationError, match="no registered parent"):
        load_location_registry_from_path(_write(tmp_path, doc))


def test_bad_timestamp_rejected(tmp_path: Path) -> None:
    doc = _reference_doc()
    doc["nodes"][0]["lastUpdated"] = "yesterday"
    with pytest.raises(LocationRegistryValidationError, match="not ISO-8601"):
        load_location_registry_from_path(_write(tmp_path, doc))


# ---------------------------------------------------------------------------
# Schema enforcement (envelope + node)
# ---------------------------------------------------------------------------


def test_envelope_schema_enforced(tmp_path: Path) -> None:
    doc = _reference_doc()
    doc["status"] = "experimental"  # not in the status enum
    with pytest.raises(LocationRegistryValidationError, match="schema validation failed"):
        load_location_registry_from_path(_write(tmp_path, doc))


def test_node_schema_enforced(tmp_path: Path) -> None:
    doc = _reference_doc()
    doc["nodes"][2]["network"]["ticCapabilityTier"] = "Tier-4"  # not in the tier enum
    with pytest.raises(LocationRegistryValidationError, match="nodes\\[2\\]"):
        load_location_registry_from_path(_write(tmp_path, doc))


def test_unknown_node_attribute_rejected(tmp_path: Path) -> None:
    doc = _reference_doc()
    doc["nodes"][0]["hrLinkage"] = {"primaryDutyStation": True}  # identity-side, not a node attribute
    with pytest.raises(LocationRegistryValidationError, match="schema validation failed"):
        load_location_registry_from_path(_write(tmp_path, doc))


def test_malformed_loc_path_rejected(tmp_path: Path) -> None:
    doc = _reference_doc()
    doc["nodes"][0]["locPath"] = "USA"  # missing leading slash
    with pytest.raises(LocationRegistryValidationError, match="schema validation failed"):
        load_location_registry_from_path(_write(tmp_path, doc))
