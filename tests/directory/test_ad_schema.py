"""AD-compatibility veneer tests (ADR-110) — read-only synthesized, non-authoritative."""

from __future__ import annotations

from uiao.directory.ad_schema import (
    ad_object_classes,
    sam_account_name,
    synthesize,
    synthetic_sid,
)
from uiao.directory.dit import build_directory

PRINCIPALS = [
    {"principal_id": "alice@uiao.gov", "principal_type": "user", "attributes": {"extensionAttribute2": "IT"}},
    {"principal_id": "svc-backup", "principal_type": "servicePrincipal", "attributes": {}},
]


def test_sam_account_name_is_sanitized_and_bounded() -> None:
    assert sam_account_name("alice@uiao.gov") == "alice"
    assert sam_account_name("weird name:chars") == "weird-name-chars"  # illegal chars -> '-'
    assert len(sam_account_name("a" * 50)) == 20  # truncated to the AD limit


def test_synthetic_sid_is_deterministic_and_namespaced() -> None:
    sid1 = synthetic_sid("alice@uiao.gov")
    sid2 = synthetic_sid("alice@uiao.gov")
    assert sid1 == sid2  # deterministic
    assert sid1.startswith("S-1-5-21-")
    # The domain (first three sub-authorities) is shared across principals.
    assert sid1.rsplit("-", 1)[0] == synthetic_sid("bob@uiao.gov").rsplit("-", 1)[0]
    # …but the RID differs per principal.
    assert sid1 != synthetic_sid("bob@uiao.gov")


def test_synthesize_advertises_non_authoritative_sid() -> None:
    veneer = synthesize("alice@uiao.gov", "user")
    assert veneer["uiaoSyntheticSid"] == ["TRUE"]  # advertised synthetic (ADR-110 §2)
    assert veneer["sAMAccountName"] == ["alice"]
    assert veneer["objectSid"][0].startswith("S-1-5-21-")


def test_object_classes_by_type() -> None:
    assert "user" in ad_object_classes("user")
    assert "computer" in ad_object_classes("device")


def test_build_directory_default_has_no_veneer() -> None:
    directory = build_directory(PRINCIPALS)
    alice = next(e for e in directory.entries if "alice" in e.dn)
    assert "sAMAccountName" not in alice.attributes
    assert "objectSid" not in alice.attributes


def test_build_directory_ad_veneer_adds_attributes() -> None:
    directory = build_directory(PRINCIPALS, ad_veneer=True)
    alice = next(e for e in directory.entries if "alice" in e.dn)
    assert alice.attributes["sAMAccountName"] == ["alice"]
    assert alice.attributes["userPrincipalName"] == ["alice@uiao.gov"]
    assert alice.attributes["objectSid"][0].startswith("S-1-5-21-")
    assert alice.attributes["uiaoSyntheticSid"] == ["TRUE"]
    # AD objectClass values merge onto the existing projection classes.
    assert "user" in alice.attributes["objectClass"]
    assert "uiaoOrgPath" in alice.attributes["objectClass"]  # governed class preserved
    # The governed facet is still present and unchanged.
    assert alice.attributes["uiaoOrgPathDepartment"] == ["IT"]


def test_service_principal_veneer_objectclass() -> None:
    directory = build_directory(PRINCIPALS, ad_veneer=True)
    svc = next(e for e in directory.entries if "svc-backup" in e.dn)
    assert svc.attributes["sAMAccountName"] == ["svc-backup"]
