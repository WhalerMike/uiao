"""Per-bind read-scoping tests (ADR-100 §5)."""

from __future__ import annotations

from uiao.directory.policy import ReadPolicy, default_read_policy
from uiao.directory.protocol import Entry

ENTRY = Entry(
    dn="cn=alice,ou=people,dc=x",
    attributes={
        "cn": ["alice"],
        "uiaoOrgPathRegion": ["NCR"],
        "uiaoOrgPathClearanceLevel": ["TopSecret"],
        "uiaoOrgPathCostCenter": ["CC-4200"],
    },
)


def test_anonymous_loses_sensitive_attributes() -> None:
    policy = ReadPolicy(sensitive_attributes=frozenset({"uiaoOrgPathClearanceLevel"}))
    scoped = policy.apply(ENTRY, authenticated=False)
    assert "uiaoOrgPathClearanceLevel" not in scoped.attributes
    assert scoped.attributes["uiaoOrgPathRegion"] == ["NCR"]
    assert scoped.dn == ENTRY.dn  # the DN is never redacted


def test_authenticated_keeps_sensitive_attributes() -> None:
    policy = ReadPolicy(sensitive_attributes=frozenset({"uiaoOrgPathClearanceLevel"}))
    scoped = policy.apply(ENTRY, authenticated=True)
    assert scoped is ENTRY  # unchanged, returned as-is


def test_matching_is_case_insensitive() -> None:
    policy = ReadPolicy(sensitive_attributes=frozenset({"uiaoorgpathclearancelevel"}))
    scoped = policy.apply(ENTRY, authenticated=False)
    assert "uiaoOrgPathClearanceLevel" not in scoped.attributes


def test_empty_policy_is_passthrough() -> None:
    policy = ReadPolicy()
    assert policy.apply(ENTRY, authenticated=False) is ENTRY


def test_default_policy_resolves_clearance_and_cost_center() -> None:
    # The default marks clearance + cost-center sensitive, named via the
    # ldap binding profile (UIAO_193) — uiaoOrgPath<Facet>.
    policy = default_read_policy()
    assert policy.is_sensitive("uiaoOrgPathClearanceLevel")
    assert policy.is_sensitive("uiaoOrgPathCostCenter")
    assert not policy.is_sensitive("uiaoOrgPathRegion")
