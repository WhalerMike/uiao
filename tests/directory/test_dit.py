"""Directory Information Tree projection + filter tests (ADR-100)."""

from __future__ import annotations

from uiao.directory.dit import build_directory, match
from uiao.directory.protocol import Entry, Filter, Scope

PRINCIPALS = [
    {
        "principal_id": "alice@uiao.gov",
        "principal_type": "user",
        "attributes": {"extensionAttribute1": "NCR", "extensionAttribute2": "IT", "extensionAttribute4": "Engineer"},
    },
    {
        "principal_id": "bob@uiao.gov",
        "principal_type": "user",
        "attributes": {"extensionAttribute2": "HR", "extensionAttribute3": ""},  # empty slot dropped
    },
    {
        "principal_id": "svc-backup",
        "principal_type": "servicePrincipal",
        "attributes": {"extensionAttribute10": "Service"},
    },
]


def test_projection_uses_binding_profile_attribute_names() -> None:
    directory = build_directory(PRINCIPALS)
    alice = next(e for e in directory.entries if "alice" in e.dn)
    # ldap binding profile (UIAO_193): extensionAttribute1 -> uiaoOrgPathRegion.
    assert alice.attributes["uiaoOrgPathRegion"] == ["NCR"]
    assert alice.attributes["uiaoOrgPathDepartment"] == ["IT"]
    assert alice.attributes["uiaoOrgPathRole"] == ["Engineer"]


def test_empty_facet_values_are_dropped() -> None:
    directory = build_directory(PRINCIPALS)
    bob = next(e for e in directory.entries if "bob" in e.dn)
    assert "uiaoOrgPathDivision" not in bob.attributes  # extensionAttribute3 was ""


def test_base_and_people_containers_present() -> None:
    directory = build_directory(PRINCIPALS, base_dn="dc=test")
    dns = [e.dn for e in directory.entries]
    assert "dc=test" in dns
    assert "ou=people,dc=test" in dns


def test_service_principal_objectclass() -> None:
    directory = build_directory(PRINCIPALS)
    svc = next(e for e in directory.entries if "svc-backup" in e.dn)
    assert "applicationProcess" in svc.attributes["objectClass"]
    assert svc.attributes["uiaoPrincipalType"] == ["servicePrincipal"]


def test_search_subtree_equality() -> None:
    directory = build_directory(PRINCIPALS)
    filt = Filter(kind="equality", attribute="uiaoOrgPathDepartment", value="IT")
    hits = directory.search("dc=agd,dc=uiao,dc=gov", Scope.WHOLE_SUBTREE, filt)
    assert [e.attributes["cn"][0] for e in hits] == ["alice@uiao.gov"]


def test_search_is_case_insensitive_on_value() -> None:
    directory = build_directory(PRINCIPALS)
    filt = Filter(kind="equality", attribute="uiaoorgpathdepartment", value="it")
    hits = directory.search("dc=agd,dc=uiao,dc=gov", Scope.WHOLE_SUBTREE, filt)
    assert len(hits) == 1


def test_search_base_scope_targets_single_entry() -> None:
    directory = build_directory(PRINCIPALS)
    present = Filter(kind="present", attribute="objectClass")
    hits = directory.search("ou=people,dc=agd,dc=uiao,dc=gov", Scope.BASE_OBJECT, present)
    assert len(hits) == 1
    assert hits[0].dn == "ou=people,dc=agd,dc=uiao,dc=gov"


def test_search_single_level_returns_children_only() -> None:
    directory = build_directory(PRINCIPALS)
    present = Filter(kind="present", attribute="objectClass")
    hits = directory.search("ou=people,dc=agd,dc=uiao,dc=gov", Scope.SINGLE_LEVEL, present)
    assert {e.attributes["cn"][0] for e in hits} == {"alice@uiao.gov", "bob@uiao.gov", "svc-backup"}


def test_and_or_not_composition() -> None:
    entry = Entry(dn="cn=x", attributes={"objectClass": ["person"], "uiaoOrgPathRegion": ["NCR"]})
    f_and = Filter(
        kind="and",
        children=(
            Filter(kind="present", attribute="objectClass"),
            Filter(kind="equality", attribute="uiaoOrgPathRegion", value="NCR"),
        ),
    )
    assert match(f_and, entry) is True
    f_not = Filter(kind="not", children=(Filter(kind="equality", attribute="uiaoOrgPathRegion", value="EMEA"),))
    assert match(f_not, entry) is True
    f_or = Filter(
        kind="or",
        children=(
            Filter(kind="equality", attribute="uiaoOrgPathRegion", value="EMEA"),
            Filter(kind="equality", attribute="uiaoOrgPathRegion", value="NCR"),
        ),
    )
    assert match(f_or, entry) is True


def test_substring_match() -> None:
    entry = Entry(dn="cn=alice@uiao.gov", attributes={"cn": ["alice@uiao.gov"]})
    filt = Filter(kind="substrings", attribute="cn", initial="al", final="gov", any=("uiao",))
    assert match(filt, entry) is True
    miss = Filter(kind="substrings", attribute="cn", initial="zz")
    assert match(miss, entry) is False


def test_principal_for_resolves_id_and_type() -> None:
    # The projected DN's RDN is sanitized; principal_for recovers the real id
    # (from the cn attribute) + type so a provider can address the object.
    directory = build_directory(PRINCIPALS)
    dn = "cn=alice-uiao.gov,ou=people,dc=agd,dc=uiao,dc=gov"
    assert directory.principal_for(dn) == ("alice@uiao.gov", "user")
    svc = "cn=svc-backup,ou=people,dc=agd,dc=uiao,dc=gov"
    assert directory.principal_for(svc) == ("svc-backup", "servicePrincipal")


def test_principal_for_returns_none_for_containers_and_unknowns() -> None:
    directory = build_directory(PRINCIPALS)
    assert directory.principal_for("ou=people,dc=agd,dc=uiao,dc=gov") is None  # container, no cn/type
    assert directory.principal_for("cn=ghost,ou=people,dc=agd,dc=uiao,dc=gov") is None  # absent
