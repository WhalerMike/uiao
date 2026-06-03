"""Tests for the AD→OrgPath assessment bridge.

Covers the mapping model + loader (`ad_mapping`), the pure facet assigner
(`ad_assign`), the directory readers (`directory_reader`), and the
`uiao orgtree assess` CLI. The live LDAP path and live Graph writes are not
exercised (no server/creds in CI) — the recording/offline seams keep every
test offline.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from uiao.modernization.orgtree.ad_assign import OrgPathAssigner
from uiao.modernization.orgtree.ad_mapping import (
    FacetRule,
    MappingError,
    OrgPathMapping,
    default_mapping,
)
from uiao.adapters.modernization.active_directory.directory_reader import (
    attributes_for_mapping,
    entry_to_record,
    read_records_from_export,
)

# A representative AD user record.
_USER = {
    "distinguishedName": "CN=jsmith,OU=IT,DC=contoso,DC=com",
    "sAMAccountName": "jsmith",
    "department": "Information Technology",
    "title": "Senior Cloud Engineer",
    "physicalDeliveryOfficeName": "Reston VA",
    "division": "Cloud",
    "employeeType": "Contractor",
    "whenCreated": "20200115103000.0Z",
    "accountExpires": "0",
    "clearanceLevel": "Secret",
    "memberOf": ["CN=Domain Admins,CN=Users,DC=contoso,DC=com"],
}


# ---------------------------------------------------------------------------
# Mapping model + loader
# ---------------------------------------------------------------------------


def test_default_mapping_covers_named_facets() -> None:
    mapping = default_mapping()
    facets = {r.facet for r in mapping.rules}
    for expected in ("region", "department", "division", "role", "classification", "account_type"):
        assert expected in facets


def test_facet_rule_rejects_bad_transform() -> None:
    with pytest.raises(MappingError):
        FacetRule(facet="department", transform="nonsense")


def test_facet_rule_rejects_bad_match() -> None:
    with pytest.raises(MappingError):
        FacetRule(facet="department", match="fuzzy")


def test_mapping_from_dict_parses_rules() -> None:
    mapping = OrgPathMapping.from_dict(
        {"facets": [{"facet": "department", "source": "department", "aliases": {"IT Dept": "IT"}}]}
    )
    rule = mapping.rule_for("department")
    assert rule is not None
    assert rule.aliases["it dept"] == "IT"  # alias keys are lowercased


def test_mapping_from_dict_rejects_empty() -> None:
    with pytest.raises(MappingError):
        OrgPathMapping.from_dict({"facets": []})


def test_mapping_from_yaml_roundtrip(tmp_path: Path) -> None:
    p = tmp_path / "m.yaml"
    p.write_text("facets:\n  - facet: department\n    source: department\n    aliases: {it: IT}\n", encoding="utf-8")
    mapping = OrgPathMapping.from_yaml(p)
    assert mapping.rule_for("department").aliases == {"it": "IT"}


# ---------------------------------------------------------------------------
# Assigner — derivation
# ---------------------------------------------------------------------------


def test_assign_derives_expected_facets() -> None:
    result = OrgPathAssigner().assign(_USER, target_type="user")
    fv = result.facet_values
    assert fv["region"] == "EASTUS"  # "Reston VA" substring
    assert fv["department"] == "IT"  # "Information Technology" alias
    assert fv["division"] == "Cloud"
    assert fv["role"] == "Engineer"  # "...Engineer" substring
    assert fv["classification"] == "Contractor"
    assert fv["hire_date"] == "2020-01-15"  # generalized-time → ISO date
    assert fv["term_date"] == ""  # accountExpires "0" = never
    assert fv["clearance_level"] == "Secret"
    assert fv["account_type"] == "Privileged"  # Domain Admins membership


def test_assign_flags_unmapped_value() -> None:
    rec = dict(_USER, department="Marketing & Comms")
    result = OrgPathAssigner().assign(rec)
    dept_findings = [f for f in result.findings if f.facet == "department"]
    assert len(dept_findings) == 1
    assert dept_findings[0].severity == "P2"
    assert "department" not in result.facet_values


def test_assign_flags_missing_source_without_default() -> None:
    # cost_center has no default and the record has no extensionAttribute5.
    result = OrgPathAssigner().assign(_USER)
    assert any(f.facet == "cost_center" for f in result.findings)


def test_assign_service_account_account_type() -> None:
    svc = {"sAMAccountName": "svc-sql", "servicePrincipalNames": ["MSSQLSvc/db01"], "department": "IT"}
    result = OrgPathAssigner().assign(svc)
    assert result.facet_values["account_type"] == "Service"


def test_assign_default_applies_when_unmapped() -> None:
    # role has default Analyst; an unmatched title falls back to it.
    rec = dict(_USER, title="Wizard of Things")
    result = OrgPathAssigner().assign(rec)
    assert result.facet_values["role"] == "Analyst"


def test_assign_result_to_dict_is_json_serializable() -> None:
    result = OrgPathAssigner().assign(_USER)
    blob = json.dumps(result.to_dict())
    data = json.loads(blob)
    assert data["target_id"] == _USER["distinguishedName"]
    assert "facet_values" in data and "findings" in data


def test_assign_tenant_override_changes_derivation() -> None:
    mapping = OrgPathMapping.from_dict(
        {"facets": [{"facet": "department", "source": "costCenterName", "aliases": {"tech": "IT"}}]}
    )
    rec = {"sAMAccountName": "u1", "costCenterName": "Tech", "department": "ignored"}
    result = OrgPathAssigner(mapping=mapping).assign(rec)
    assert result.facet_values["department"] == "IT"


# ---------------------------------------------------------------------------
# Directory readers
# ---------------------------------------------------------------------------


def test_attributes_for_mapping_includes_sources_and_always() -> None:
    attrs = attributes_for_mapping(default_mapping())
    assert "department" in attrs and "title" in attrs  # rule sources
    assert "memberOf" in attrs and "servicePrincipalNames" in attrs  # always-needed


def test_entry_to_record_flattens_single_and_multi() -> None:
    # Mimics ldap3 Entry.entry_attributes_as_dict (every value is a list).
    attrs_dict = {
        "department": ["IT"],
        "memberOf": ["CN=A,DC=x", "CN=B,DC=x"],
        "title": [],  # empty → omitted
    }
    rec = entry_to_record(attrs_dict, ["department", "memberOf", "title", "absent"])
    assert rec["department"] == "IT"  # single value collapsed
    assert rec["memberOf"] == ["CN=A,DC=x", "CN=B,DC=x"]  # multi kept as list
    assert "title" not in rec and "absent" not in rec


def test_read_records_from_export_list(tmp_path: Path) -> None:
    p = tmp_path / "ad.json"
    p.write_text(json.dumps([_USER]), encoding="utf-8")
    records = read_records_from_export(p)
    assert len(records) == 1 and records[0]["sAMAccountName"] == "jsmith"


def test_read_records_from_export_keyed(tmp_path: Path) -> None:
    p = tmp_path / "ad.json"
    p.write_text(json.dumps({"users": [_USER]}), encoding="utf-8")
    assert len(read_records_from_export(p)) == 1


def test_read_records_from_export_rejects_garbage(tmp_path: Path) -> None:
    p = tmp_path / "ad.json"
    p.write_text(json.dumps({"nope": 1}), encoding="utf-8")
    with pytest.raises(ValueError):
        read_records_from_export(p)
