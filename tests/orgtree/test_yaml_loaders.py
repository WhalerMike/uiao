"""Tests for the Model C YAML loaders (ADR-084 §C1).

Each consumer module ships a ``load_*()`` function that reads its
canonical YAML library + validates against its JSON Schema + builds
the consumer object. These tests run against the canon-shipped YAML
under ``src/uiao/canon/data/orgpath/`` and verify:

* every consumer's YAML loader returns a non-empty consumer object
* JSON-Schema validation rejects malformed input
* Value Drift in the YAML against the codebook is caught at load time
* device-planes YAML routing matches the hardcoded planner routing
"""

from __future__ import annotations


import pytest
import yaml

from uiao.modernization.orgtree._yaml_loaders import (
    YamlLibraryValidationError,
)
from uiao.modernization.orgtree.admin_units import (
    AdminUnitRegistry,
    load_admin_unit_registry,
)
from uiao.modernization.orgtree.codebook import default_codebook
from uiao.modernization.orgtree.device_orgpath import load_disposition_routing
from uiao.modernization.orgtree.dynamic_groups import (
    DynamicGroupLibrary,
    load_dynamic_group_library,
)
from uiao.modernization.orgtree.policy_targeting import (
    PolicyTargetLibrary,
    load_policy_target_library,
)
from uiao.modernization.orgtree.rule_renderer import RuleRenderError


@pytest.fixture
def real_codebook():
    return default_codebook()


# ---------------------------------------------------------------------------
# Default-resource loading (the canon-shipped YAMLs under src/uiao/canon/)
# ---------------------------------------------------------------------------


def test_dynamic_group_library_loads_from_canon_yaml(real_codebook):
    lib = load_dynamic_group_library(real_codebook)
    assert isinstance(lib, DynamicGroupLibrary)
    assert len(lib.groups) >= 5
    for spec in lib.groups.values():
        assert spec.rule.startswith("(")  # rendered successfully


def test_admin_unit_registry_loads_from_canon_yaml(real_codebook):
    reg = load_admin_unit_registry(real_codebook)
    assert isinstance(reg, AdminUnitRegistry)
    assert len(reg.units) >= 3
    for spec in reg.units.values():
        assert spec.restricted_management is True  # canon doctrine


def test_policy_target_library_loads_from_canon_yaml(real_codebook):
    lib = load_policy_target_library(real_codebook)
    assert isinstance(lib, PolicyTargetLibrary)
    assert len(lib.targets) >= 3
    transports = {t.transport for t in lib.targets.values()}
    # The canon library exercises multiple transports
    assert "ca" in transports


def test_device_planes_loads_canonical_routing():
    routing = load_disposition_routing()
    # Canon must declare at least the hardcoded set + their planes match.
    assert routing.get("ENTRA-DEVICE") == "entra"
    assert routing.get("ARC-SERVER") == "arm"
    assert routing.get("STAY-AD-DC") == "skip"
    assert routing.get("DECOMMISSION") == "skip"


# ---------------------------------------------------------------------------
# YAML override (used by deployment-specific tenants)
# ---------------------------------------------------------------------------


def test_dynamic_group_library_loads_from_alternate_yaml(real_codebook, tmp_path):
    custom = tmp_path / "custom-dg.yaml"
    custom.write_text(
        yaml.safe_dump(
            {
                "schema_version": "1.0.0",
                "library_version": "0.0.1",
                "groups": [
                    {
                        "name": "OrgTree-Custom-Test",
                        "category": "Region",
                        "description": "tenant-custom test group",
                        "composition": {"predicates": [{"facet": "region", "op": "-eq", "value": "NCR"}]},
                    }
                ],
            }
        )
    )
    lib = load_dynamic_group_library(real_codebook, yaml_path=custom)
    assert "OrgTree-Custom-Test" in lib.groups


def test_admin_unit_registry_loads_from_alternate_yaml(real_codebook, tmp_path):
    custom = tmp_path / "custom-au.yaml"
    custom.write_text(
        yaml.safe_dump(
            {
                "schema_version": "1.0.0",
                "registry_version": "0.0.1",
                "units": [
                    {
                        "name": "AU-Custom-Test",
                        "description": "tenant-custom AU",
                        "composition": {"predicates": [{"facet": "region", "op": "-eq", "value": "NCR"}]},
                    }
                ],
            }
        )
    )
    reg = load_admin_unit_registry(real_codebook, yaml_path=custom)
    assert "AU-Custom-Test" in reg.units


# ---------------------------------------------------------------------------
# Schema validation rejects malformed input
# ---------------------------------------------------------------------------


def test_dynamic_group_library_rejects_missing_required_field(real_codebook, tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text(
        yaml.safe_dump(
            {
                "schema_version": "1.0.0",
                "library_version": "0.0.1",
                # missing "groups"
            }
        )
    )
    with pytest.raises(YamlLibraryValidationError, match="schema validation"):
        load_dynamic_group_library(real_codebook, yaml_path=bad)


def test_dynamic_group_library_rejects_invalid_name_prefix(real_codebook, tmp_path):
    bad = tmp_path / "bad2.yaml"
    bad.write_text(
        yaml.safe_dump(
            {
                "schema_version": "1.0.0",
                "library_version": "0.0.1",
                "groups": [
                    {
                        "name": "NotOrgTreePrefixed",  # doesn't match OrgTree- regex
                        "category": "Region",
                        "description": "x",
                        "composition": {"predicates": [{"facet": "region", "op": "-eq", "value": "NCR"}]},
                    }
                ],
            }
        )
    )
    with pytest.raises(YamlLibraryValidationError):
        load_dynamic_group_library(real_codebook, yaml_path=bad)


def test_policy_target_library_rejects_unknown_transport_via_schema(real_codebook, tmp_path):
    bad = tmp_path / "bad-pt.yaml"
    bad.write_text(
        yaml.safe_dump(
            {
                "schema_version": "1.0.0",
                "library_version": "0.0.1",
                "targets": [
                    {
                        "assignment_name": "X",
                        "policy_definition_id": "y",
                        "transport": "bogus-transport",  # not in enum
                        "description": "x",
                        "composition": {"predicates": [{"facet": "region", "op": "-eq", "value": "NCR"}]},
                    }
                ],
            }
        )
    )
    with pytest.raises(YamlLibraryValidationError):
        load_policy_target_library(real_codebook, yaml_path=bad)


def test_device_planes_rejects_invalid_plane(tmp_path):
    bad = tmp_path / "bad-dp.yaml"
    bad.write_text(
        yaml.safe_dump(
            {
                "schema_version": "1.0.0",
                "registry_version": "0.0.1",
                "dispositions": [
                    {
                        "name": "BAD-PLANE-DISP",
                        "plane": "mars",  # not in enum
                        "description": "x",
                    }
                ],
            }
        )
    )
    with pytest.raises(YamlLibraryValidationError):
        load_disposition_routing(yaml_path=bad)


# ---------------------------------------------------------------------------
# Value Drift in YAML caught at render time (ADR-084 §C3)
# ---------------------------------------------------------------------------


def test_yaml_value_drift_caught_at_render_time(real_codebook, tmp_path):
    """A YAML library that references an unknown enum value fails LOAD, not runtime."""
    bad = tmp_path / "yaml-with-value-drift.yaml"
    bad.write_text(
        yaml.safe_dump(
            {
                "schema_version": "1.0.0",
                "library_version": "0.0.1",
                "groups": [
                    {
                        "name": "OrgTree-Mars-Users",
                        "category": "Region",
                        "description": "Mars-only group",
                        "composition": {"predicates": [{"facet": "region", "op": "-eq", "value": "MARS"}]},
                    }
                ],
            }
        )
    )
    with pytest.raises(RuleRenderError, match="not active for facet 'region'"):
        load_dynamic_group_library(real_codebook, yaml_path=bad)


# ---------------------------------------------------------------------------
# device-planes YAML matches the hardcoded planner routing
# ---------------------------------------------------------------------------


def test_device_planes_yaml_matches_planner_hardcoded_routing():
    """The canonical YAML's disposition routing must match the planner's hardcoded sets.

    If a future operator adds a new disposition to the YAML, the
    planner's hardcoded sets MUST also be updated — this test catches
    drift between the audit-friendly YAML and the runtime sets.
    """
    from uiao.modernization.orgtree.device_orgpath import (
        _ARM_DISPOSITIONS,
        _ENTRA_DISPOSITIONS,
        _SKIP_DISPOSITIONS,
    )

    routing = load_disposition_routing()
    entra = {n for n, p in routing.items() if p == "entra"}
    arm = {n for n, p in routing.items() if p == "arm"}
    skip = {n for n, p in routing.items() if p == "skip"}

    assert entra == set(_ENTRA_DISPOSITIONS)
    assert arm == set(_ARM_DISPOSITIONS)
    assert skip == set(_SKIP_DISPOSITIONS)


# ---------------------------------------------------------------------------
# Drift-engine-config schema (no YAML loader; schema only for validation)
# ---------------------------------------------------------------------------


def test_drift_engine_config_schema_validates_minimal_doc():
    """The drift-engine-config schema accepts a minimal config + per-facet policies."""
    import json
    from importlib import resources

    schema = json.loads(
        resources.files("uiao.schemas.orgpath").joinpath("drift-engine-config.schema.json").read_text(encoding="utf-8")
    )
    import jsonschema

    # Minimal valid doc
    jsonschema.validate(
        instance={"schema_version": "1.0.0"},
        schema=schema,
    )
    # With per-facet policies
    jsonschema.validate(
        instance={
            "schema_version": "1.0.0",
            "dry_run": False,
            "halt_on_critical": "P2",
            "facet_policies": {
                "department": {
                    "auto_remediate_value_drift": True,
                    "auto_remediate_phantom_drift": False,
                }
            },
        },
        schema=schema,
    )
    # Invalid halt level
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(
            instance={"schema_version": "1.0.0", "halt_on_critical": "P9"},
            schema=schema,
        )
