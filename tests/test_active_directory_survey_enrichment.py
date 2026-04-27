"""
tests/test_active_directory_survey_enrichment.py
-------------------------------------------------
Unit tests for WS-A1 Phase 1 AD survey enrichment features:

  1. Nested group resolution with cycle detection
  2. Disabled / stale account flagging (userAccountControl bits + lastLogonTimestamp)
  3. Orphaned SID detection in group memberships
  4. Manager chain resolution (with cycle guard)
  5. OU-derived candidate OrgPath per user

All tests use synthetic in-memory AD records — no live LDAP connection required.

Canon reference: UIAO_007_OrgTree_Modernization_AD_to_EntraID_v1.0
"""

from __future__ import annotations

import datetime
import json


from uiao.adapters.modernization.active_directory.survey import (
    ADSurveyReport,
    UAC_ACCOUNTDISABLE,
    UAC_DONT_EXPIRE_PASSWORD,
    UAC_LOCKOUT,
    UAC_PASSWD_NOTREQD,
    decode_account_flags,
    derive_candidate_orgpath,
    detect_orphaned_sids,
    emit_enrichment_findings,
    enrich_user,
    is_stale_account,
    resolve_group_members,
    resolve_manager_chain,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BASE_DN = "DC=corp,DC=contoso,DC=com"


def _build_windows_filetime(days_ago: int) -> int:
    """
    Build a Windows FILETIME value for a login *days_ago* days in the past.

    Windows FILETIME = 100-nanosecond intervals since 1601-01-01.
    """
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    logon_dt = now - datetime.timedelta(days=days_ago)
    unix_seconds = logon_dt.timestamp()
    # Seconds between Windows epoch (1601-01-01) and Unix epoch (1970-01-01)
    _EPOCH_DIFF_S: int = 11_644_473_600
    windows_seconds = unix_seconds + _EPOCH_DIFF_S
    return int(windows_seconds * 10_000_000)


# ---------------------------------------------------------------------------
# Synthetic AD forest object index
# Keys are DNs; values are attribute dicts mirroring the shape enrich_user
# expects (all keys optional for flexibility).
# ---------------------------------------------------------------------------


def _make_synthetic_forest() -> dict[str, dict]:
    return {
        # ------ Users ------
        "CN=Alice,OU=Finance,DC=corp,DC=contoso,DC=com": {
            "object_class": "user",
            "sAMAccountName": "alice",
            "userAccountControl": 512,  # normal active account
            "lastLogonTimestamp": None,  # never logged in → stale
            "manager": "CN=Bob,OU=Finance,DC=corp,DC=contoso,DC=com",
            "memberOf": [
                "CN=FinanceGroup,OU=Groups,DC=corp,DC=contoso,DC=com",
            ],
        },
        "CN=Bob,OU=Finance,DC=corp,DC=contoso,DC=com": {
            "object_class": "user",
            "sAMAccountName": "bob",
            "userAccountControl": 512,
            "lastLogonTimestamp": _build_windows_filetime(30),
            "manager": None,
            "memberOf": [],
        },
        "CN=Carol,OU=Engineering,DC=corp,DC=contoso,DC=com": {
            "object_class": "user",
            "sAMAccountName": "carol",
            "userAccountControl": UAC_ACCOUNTDISABLE | UAC_DONT_EXPIRE_PASSWORD,
            "lastLogonTimestamp": _build_windows_filetime(200),
            "manager": "CN=Bob,OU=Finance,DC=corp,DC=contoso,DC=com",
            "memberOf": [],
        },
        # Dave → Eve → Dave creates a manager cycle
        "CN=Dave,OU=IT,OU=US,DC=corp,DC=contoso,DC=com": {
            "object_class": "user",
            "sAMAccountName": "dave",
            "userAccountControl": 512,
            "lastLogonTimestamp": _build_windows_filetime(10),
            "manager": "CN=Eve,OU=IT,OU=US,DC=corp,DC=contoso,DC=com",
            "memberOf": [],
        },
        "CN=Eve,OU=IT,OU=US,DC=corp,DC=contoso,DC=com": {
            "object_class": "user",
            "sAMAccountName": "eve",
            "userAccountControl": 512,
            "lastLogonTimestamp": _build_windows_filetime(5),
            "manager": "CN=Dave,OU=IT,OU=US,DC=corp,DC=contoso,DC=com",
            "memberOf": [],
        },
        # ------ Groups ------
        "CN=FinanceGroup,OU=Groups,DC=corp,DC=contoso,DC=com": {
            "object_class": "group",
            "members": [
                "CN=Alice,OU=Finance,DC=corp,DC=contoso,DC=com",
                "CN=BudgetSubGroup,OU=Groups,DC=corp,DC=contoso,DC=com",
                # Orphaned SID — foreign security principal pattern
                "CN=S-1-5-21-111-222-333-1001,CN=ForeignSecurityPrincipals,DC=corp,DC=contoso,DC=com",
            ],
        },
        "CN=BudgetSubGroup,OU=Groups,DC=corp,DC=contoso,DC=com": {
            "object_class": "group",
            "members": [
                "CN=Alice,OU=Finance,DC=corp,DC=contoso,DC=com",
            ],
        },
        # Cyclic groups: GroupA → GroupB → GroupA
        "CN=GroupA,OU=Groups,DC=corp,DC=contoso,DC=com": {
            "object_class": "group",
            "members": [
                "CN=GroupB,OU=Groups,DC=corp,DC=contoso,DC=com",
            ],
        },
        "CN=GroupB,OU=Groups,DC=corp,DC=contoso,DC=com": {
            "object_class": "group",
            "members": [
                "CN=GroupA,OU=Groups,DC=corp,DC=contoso,DC=com",
            ],
        },
    }


# Module-level forest used by all tests (re-created per test class if mutation risk)
_FOREST = _make_synthetic_forest()


# ===========================================================================
# Deliverable 1: Nested group resolution with cycle detection
# ===========================================================================


class TestNestedGroupResolution:
    """Deliverable 1 — recursive group expansion + cycle break."""

    def test_flat_group_expansion(self) -> None:
        """Direct members of a flat group are returned."""
        budget_dn = "CN=BudgetSubGroup,OU=Groups,DC=corp,DC=contoso,DC=com"
        members, cycle = resolve_group_members(budget_dn, _FOREST)
        assert "CN=Alice,OU=Finance,DC=corp,DC=contoso,DC=com" in members
        assert cycle is False

    def test_nested_group_expansion(self) -> None:
        """Members of nested sub-groups are included in the flat result, deduplicated."""
        finance_dn = "CN=FinanceGroup,OU=Groups,DC=corp,DC=contoso,DC=com"
        members, cycle = resolve_group_members(finance_dn, _FOREST)
        alice_dn = "CN=Alice,OU=Finance,DC=corp,DC=contoso,DC=com"
        assert members.count(alice_dn) == 1, "Alice must appear exactly once (deduplicated)"
        budget_dn = "CN=BudgetSubGroup,OU=Groups,DC=corp,DC=contoso,DC=com"
        assert budget_dn in members

    def test_cycle_detected_and_halted(self) -> None:
        """Cyclic membership is detected without infinite loop."""
        group_a_dn = "CN=GroupA,OU=Groups,DC=corp,DC=contoso,DC=com"
        members, cycle = resolve_group_members(group_a_dn, _FOREST)
        assert cycle is True, "Cycle flag must be True for GroupA → GroupB → GroupA"
        group_b_dn = "CN=GroupB,OU=Groups,DC=corp,DC=contoso,DC=com"
        assert group_b_dn in members

    def test_unknown_group_dn_returns_empty(self) -> None:
        """A DN not in the index returns empty with no cycle."""
        members, cycle = resolve_group_members("CN=Ghost,DC=corp,DC=contoso,DC=com", _FOREST)
        assert members == []
        assert cycle is False

    def test_group_memberships_cycle_via_enrich(self) -> None:
        """enrich_user sets group_memberships_cycle=True when user belongs to cyclic group."""
        user_obj = {
            "object_class": "user",
            "sAMAccountName": "frank",
            "userAccountControl": 512,
            "lastLogonTimestamp": _build_windows_filetime(10),
            "manager": None,
            "memberOf": ["CN=GroupA,OU=Groups,DC=corp,DC=contoso,DC=com"],
        }
        user_dn = "CN=Frank,OU=IT,OU=US,DC=corp,DC=contoso,DC=com"
        enrichment = enrich_user(user_dn, user_obj, _FOREST, set())
        assert enrichment.group_memberships_cycle is True

    def test_group_cycle_finding_emitted(self) -> None:
        """emit_enrichment_findings produces a GOV-MIG-014 finding for cyclic groups."""
        user_obj = {
            "object_class": "user",
            "sAMAccountName": "frank",
            "userAccountControl": 512,
            "lastLogonTimestamp": _build_windows_filetime(10),
            "manager": None,
            "memberOf": ["CN=GroupA,OU=Groups,DC=corp,DC=contoso,DC=com"],
        }
        user_dn = "CN=Frank,OU=IT,OU=US,DC=corp,DC=contoso,DC=com"
        enrichment = enrich_user(user_dn, user_obj, _FOREST, set())
        report = ADSurveyReport(forest_root=_BASE_DN)
        emit_enrichment_findings(enrichment, report, _BASE_DN)
        cycle_findings = [f for f in report.findings if "GOV-MIG-014" in f.error_code]
        assert len(cycle_findings) >= 1


# ===========================================================================
# Deliverable 2: Disabled / stale account flagging
# ===========================================================================


class TestFiletimeConversion:
    """Regression: lastLogonTimestamp FILETIME → datetime conversion (MS-ADTS 2.2.18).

    Windows FILETIME = 100-nanosecond intervals since 1601-01-01 UTC.
    133_485_408_000_000_000 = 2024-01-01T00:00:00Z (exact).
    If the value were mistakenly treated as Unix epoch seconds the logon
    date would be computed as year ~5231, making every account appear non-stale.
    If treated as Unix milliseconds the date would be ~6220.
    The correct conversion yields 2024-01-01, which is >90 days before today
    and thus stale.
    """

    # FILETIME for 2024-01-01T00:00:00Z:
    # (datetime(2024,1,1,tzinfo=timezone.utc) - datetime(1601,1,1,tzinfo=timezone.utc)).total_seconds() * 10_000_000
    # = 133_485_408_000_000_000
    _FILETIME_2024_01_01: int = 133_485_408_000_000_000

    # Expected days between 2024-01-01 and now, computed at import time so
    # the test stays green as wall-clock advances (no hardcoded upper bound).
    _EXPECTED_DAYS: int = (
        datetime.datetime.now(tz=datetime.timezone.utc)
        - datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)
    ).days

    def test_known_filetime_not_treated_as_unix_epoch(self) -> None:
        """2024-01-01 FILETIME must be interpreted as year 2024, not ~5231."""
        stale, days = is_stale_account(self._FILETIME_2024_01_01, stale_days=90)
        # 2024-01-01 is well over 90 days in the past → must be stale
        assert stale is True, (
            "FILETIME 133_485_408_000_000_000 should map to 2024-01-01 (>90 d stale). "
            "If this fails, is_stale_account is misinterpreting the epoch."
        )
        # days delta must be close to today - 2024-01-01 (allow ±3 for CI clock drift)
        assert abs(days - self._EXPECTED_DAYS) <= 3, (
            f"Expected ~{self._EXPECTED_DAYS} days since 2024-01-01, got {days}"
        )

    def test_known_filetime_round_trip_days(self) -> None:
        """Verify delta_days matches independently computed days since 2024-01-01."""
        _, days = is_stale_account(self._FILETIME_2024_01_01, stale_days=9999)
        assert abs(days - self._EXPECTED_DAYS) <= 3, (
            f"Expected ~{self._EXPECTED_DAYS}, got {days}"
        )

    def test_near_future_filetime_not_stale(self) -> None:
        """A FILETIME representing 'yesterday' must never be stale."""
        ts = _build_windows_filetime(1)  # 1 day ago
        stale, days = is_stale_account(ts, stale_days=90)
        assert stale is False
        assert 0 <= days <= 3


class TestAccountFlagging:
    """Deliverable 2 — userAccountControl bit decoding + stale detection."""

    def test_decode_normal_account(self) -> None:
        flags = decode_account_flags(512)
        assert flags.disabled is False
        assert flags.locked_out is False
        assert flags.password_not_required is False
        assert flags.password_never_expires is False

    def test_decode_disabled_account(self) -> None:
        assert decode_account_flags(UAC_ACCOUNTDISABLE).disabled is True

    def test_decode_locked_out(self) -> None:
        assert decode_account_flags(UAC_LOCKOUT).locked_out is True

    def test_decode_password_not_required(self) -> None:
        assert decode_account_flags(UAC_PASSWD_NOTREQD).password_not_required is True

    def test_decode_password_never_expires(self) -> None:
        assert decode_account_flags(UAC_DONT_EXPIRE_PASSWORD).password_never_expires is True

    def test_decode_combined_flags(self) -> None:
        uac = UAC_ACCOUNTDISABLE | UAC_DONT_EXPIRE_PASSWORD
        flags = decode_account_flags(uac)
        assert flags.disabled is True
        assert flags.password_never_expires is True
        assert flags.locked_out is False

    def test_uac_constants_are_named(self) -> None:
        """UAC constants must be module-level named constants, not magic numbers."""
        assert UAC_ACCOUNTDISABLE == 0x0002
        assert UAC_LOCKOUT == 0x0010
        assert UAC_PASSWD_NOTREQD == 0x0020
        assert UAC_DONT_EXPIRE_PASSWORD == 0x10000

    def test_never_logged_in_is_stale(self) -> None:
        stale, days = is_stale_account(None)
        assert stale is True
        assert days == -1

    def test_zero_timestamp_is_stale(self) -> None:
        stale, days = is_stale_account(0)
        assert stale is True
        assert days == -1

    def test_recent_logon_not_stale(self) -> None:
        ts = _build_windows_filetime(10)
        stale, days = is_stale_account(ts, stale_days=90)
        assert stale is False
        assert days <= 15

    def test_old_logon_is_stale(self) -> None:
        ts = _build_windows_filetime(200)
        stale, days = is_stale_account(ts, stale_days=90)
        assert stale is True
        assert days >= 190

    def test_configurable_stale_threshold(self) -> None:
        ts = _build_windows_filetime(30)
        assert is_stale_account(ts, stale_days=60)[0] is False
        assert is_stale_account(ts, stale_days=20)[0] is True

    def test_enrich_flags_disabled_carol(self) -> None:
        carol_dn = "CN=Carol,OU=Engineering,DC=corp,DC=contoso,DC=com"
        enrichment = enrich_user(carol_dn, _FOREST[carol_dn], _FOREST, set())
        assert enrichment.account_flags.disabled is True
        assert enrichment.account_flags.password_never_expires is True
        assert enrichment.is_stale is True

    def test_emit_disabled_finding(self) -> None:
        carol_dn = "CN=Carol,OU=Engineering,DC=corp,DC=contoso,DC=com"
        enrichment = enrich_user(carol_dn, _FOREST[carol_dn], _FOREST, set())
        report = ADSurveyReport(forest_root=_BASE_DN)
        emit_enrichment_findings(enrichment, report, _BASE_DN)
        disabled_findings = [f for f in report.findings if "disabled" in f.detail.lower()]
        assert len(disabled_findings) >= 1

    def test_emit_stale_finding(self) -> None:
        carol_dn = "CN=Carol,OU=Engineering,DC=corp,DC=contoso,DC=com"
        enrichment = enrich_user(carol_dn, _FOREST[carol_dn], _FOREST, set())
        report = ADSurveyReport(forest_root=_BASE_DN)
        emit_enrichment_findings(enrichment, report, _BASE_DN)
        stale_findings = [f for f in report.findings if "GOV-MIG-011" in f.error_code]
        assert len(stale_findings) >= 1

    def test_emit_locked_out_finding(self) -> None:
        locked_dn = "CN=LockedUser,OU=Finance,DC=corp,DC=contoso,DC=com"
        locked_obj = {
            "object_class": "user",
            "sAMAccountName": "lockeduser",
            "userAccountControl": UAC_LOCKOUT,
            "lastLogonTimestamp": _build_windows_filetime(5),
            "manager": None,
            "memberOf": [],
        }
        forest = {**_FOREST, locked_dn: locked_obj}
        enrichment = enrich_user(locked_dn, locked_obj, forest, set())
        report = ADSurveyReport(forest_root=_BASE_DN)
        emit_enrichment_findings(enrichment, report, _BASE_DN)
        lockout_findings = [f for f in report.findings if "locked out" in f.detail.lower()]
        assert len(lockout_findings) >= 1


# ===========================================================================
# Deliverable 3: Orphaned SID detection
# ===========================================================================


class TestOrphanedSidDetection:
    """Deliverable 3 — SIDs in group memberships that don't resolve."""

    def test_orphaned_sid_detected(self) -> None:
        members = [
            "CN=Alice,OU=Finance,DC=corp,DC=contoso,DC=com",
            "CN=S-1-5-21-111-222-333-1001,CN=ForeignSecurityPrincipals,DC=corp,DC=contoso,DC=com",
        ]
        orphans = detect_orphaned_sids(members, _FOREST)
        assert "S-1-5-21-111-222-333-1001" in orphans

    def test_no_false_positive_for_real_objects(self) -> None:
        members = [
            "CN=Alice,OU=Finance,DC=corp,DC=contoso,DC=com",
            "CN=Bob,OU=Finance,DC=corp,DC=contoso,DC=com",
        ]
        assert detect_orphaned_sids(members, _FOREST) == []

    def test_no_false_positive_for_non_sid_dns(self) -> None:
        members = ["CN=SomeComputer,OU=Computers,DC=corp,DC=contoso,DC=com"]
        assert detect_orphaned_sids(members, _FOREST) == []

    def test_enrich_user_surfaces_orphaned_sid_via_group(self) -> None:
        alice_dn = "CN=Alice,OU=Finance,DC=corp,DC=contoso,DC=com"
        enrichment = enrich_user(alice_dn, _FOREST[alice_dn], _FOREST, set())
        assert any("S-1-5-21-111-222-333-1001" in sid for sid in enrichment.orphaned_sids)

    def test_emit_orphaned_sid_finding(self) -> None:
        alice_dn = "CN=Alice,OU=Finance,DC=corp,DC=contoso,DC=com"
        enrichment = enrich_user(alice_dn, _FOREST[alice_dn], _FOREST, set())
        report = ADSurveyReport(forest_root=_BASE_DN)
        emit_enrichment_findings(enrichment, report, _BASE_DN)
        sid_findings = [f for f in report.findings if "GOV-MIG-013" in f.error_code]
        assert len(sid_findings) >= 1
        assert any("S-1-5-21-111-222-333-1001" in f.detail for f in sid_findings)

    def test_multiple_orphaned_sids_produce_multiple_findings(self) -> None:
        user_dn = "CN=MultiSID,OU=Finance,DC=corp,DC=contoso,DC=com"
        user_obj = {
            "object_class": "user",
            "sAMAccountName": "multisid",
            "userAccountControl": 512,
            "lastLogonTimestamp": _build_windows_filetime(5),
            "manager": None,
            "memberOf": [],
        }
        # A group with two orphaned SIDs
        group_dn = "CN=OrphanGroup,OU=Groups,DC=corp,DC=contoso,DC=com"
        group_obj = {
            "object_class": "group",
            "members": [
                "CN=S-1-5-21-100-200-300-1001,CN=ForeignSecurityPrincipals,DC=corp,DC=contoso,DC=com",
                "CN=S-1-5-21-100-200-300-1002,CN=ForeignSecurityPrincipals,DC=corp,DC=contoso,DC=com",
            ],
        }
        forest = {**_FOREST, user_dn: user_obj, group_dn: group_obj}
        user_obj_with_group = {**user_obj, "memberOf": [group_dn]}
        enrichment = enrich_user(user_dn, user_obj_with_group, forest, set())
        assert len(enrichment.orphaned_sids) == 2


# ===========================================================================
# Deliverable 4: Manager chain resolution
# ===========================================================================


class TestManagerChainResolution:
    """Deliverable 4 — manager DN walk up to root or cycle."""

    def test_single_manager_chain(self) -> None:
        """Alice → Bob (no further manager)."""
        alice_dn = "CN=Alice,OU=Finance,DC=corp,DC=contoso,DC=com"
        chain, cycle = resolve_manager_chain(alice_dn, _FOREST)
        assert chain == ["CN=Bob,OU=Finance,DC=corp,DC=contoso,DC=com"]
        assert cycle is False

    def test_no_manager_returns_empty(self) -> None:
        """Bob has no manager."""
        bob_dn = "CN=Bob,OU=Finance,DC=corp,DC=contoso,DC=com"
        chain, cycle = resolve_manager_chain(bob_dn, _FOREST)
        assert chain == []
        assert cycle is False

    def test_cyclic_manager_chain_detected(self) -> None:
        """Dave → Eve → Dave: cycle must be detected."""
        dave_dn = "CN=Dave,OU=IT,OU=US,DC=corp,DC=contoso,DC=com"
        chain, cycle = resolve_manager_chain(dave_dn, _FOREST)
        eve_dn = "CN=Eve,OU=IT,OU=US,DC=corp,DC=contoso,DC=com"
        assert eve_dn in chain
        assert cycle is True

    def test_unknown_dn_returns_empty(self) -> None:
        chain, cycle = resolve_manager_chain("CN=Ghost,DC=corp,DC=contoso,DC=com", _FOREST)
        assert chain == []
        assert cycle is False

    def test_enrich_user_manager_chain_populated(self) -> None:
        alice_dn = "CN=Alice,OU=Finance,DC=corp,DC=contoso,DC=com"
        enrichment = enrich_user(alice_dn, _FOREST[alice_dn], _FOREST, set())
        assert enrichment.manager_chain == ["CN=Bob,OU=Finance,DC=corp,DC=contoso,DC=com"]
        assert enrichment.manager_chain_cycle is False

    def test_enrich_user_manager_cycle_flagged(self) -> None:
        dave_dn = "CN=Dave,OU=IT,OU=US,DC=corp,DC=contoso,DC=com"
        enrichment = enrich_user(dave_dn, _FOREST[dave_dn], _FOREST, set())
        assert enrichment.manager_chain_cycle is True

    def test_emit_manager_cycle_finding(self) -> None:
        dave_dn = "CN=Dave,OU=IT,OU=US,DC=corp,DC=contoso,DC=com"
        enrichment = enrich_user(dave_dn, _FOREST[dave_dn], _FOREST, set())
        report = ADSurveyReport(forest_root=_BASE_DN)
        emit_enrichment_findings(enrichment, report, _BASE_DN)
        cycle_findings = [f for f in report.findings if "GOV-MIG-012" in f.error_code]
        assert len(cycle_findings) == 1

    def test_multi_hop_manager_chain(self) -> None:
        """Test a 3-hop chain: User → Mgr1 → Mgr2 (no cycle)."""
        forest = {
            "CN=User1,OU=IT,DC=corp,DC=contoso,DC=com": {
                "object_class": "user",
                "manager": "CN=Mgr1,OU=IT,DC=corp,DC=contoso,DC=com",
                "memberOf": [],
            },
            "CN=Mgr1,OU=IT,DC=corp,DC=contoso,DC=com": {
                "object_class": "user",
                "manager": "CN=Mgr2,OU=IT,DC=corp,DC=contoso,DC=com",
                "memberOf": [],
            },
            "CN=Mgr2,OU=IT,DC=corp,DC=contoso,DC=com": {
                "object_class": "user",
                "manager": None,
                "memberOf": [],
            },
        }
        chain, cycle = resolve_manager_chain("CN=User1,OU=IT,DC=corp,DC=contoso,DC=com", forest)
        assert chain == [
            "CN=Mgr1,OU=IT,DC=corp,DC=contoso,DC=com",
            "CN=Mgr2,OU=IT,DC=corp,DC=contoso,DC=com",
        ]
        assert cycle is False


# ===========================================================================
# Deliverable 5: OU-derived candidate OrgPath per user
# ===========================================================================


class TestCandidateOrgPath:
    """Deliverable 5 — derive_candidate_orgpath from DN's OU components."""

    def test_functional_finance_ou(self) -> None:
        dn = "CN=Alice,OU=Finance,DC=corp,DC=contoso,DC=com"
        candidate = derive_candidate_orgpath(dn, set())
        assert candidate is not None
        assert "FIN" in candidate

    def test_functional_engineering_ou(self) -> None:
        dn = "CN=Carol,OU=Engineering,DC=corp,DC=contoso,DC=com"
        candidate = derive_candidate_orgpath(dn, set())
        assert candidate is not None
        assert "ENG" in candidate

    def test_functional_it_ou(self) -> None:
        dn = "CN=SomeUser,OU=IT,DC=corp,DC=contoso,DC=com"
        candidate = derive_candidate_orgpath(dn, set())
        assert candidate is not None
        assert "IT" in candidate

    def test_unresolvable_segment_returns_none(self) -> None:
        # "Baltimore" is 9 chars — exceeds the 6-char limit for _normalize_segment,
        # so no candidate OrgPath can be derived from this DN.
        dn = "CN=User,OU=Baltimore,OU=EastRegion,DC=corp,DC=contoso,DC=com"
        candidate = derive_candidate_orgpath(dn, set())
        assert candidate is None

    def test_codebook_hit_returns_code(self) -> None:
        dn = "CN=Alice,OU=Finance,DC=corp,DC=contoso,DC=com"
        codebook = {"ORG-FIN"}
        candidate = derive_candidate_orgpath(dn, codebook)
        assert candidate == "ORG-FIN"

    def test_candidate_format_starts_with_org(self) -> None:
        dn = "CN=Alice,OU=Finance,DC=corp,DC=contoso,DC=com"
        candidate = derive_candidate_orgpath(dn, set())
        assert candidate is not None
        assert candidate.startswith("ORG-")

    def test_enrich_user_candidate_orgpath_finance(self) -> None:
        alice_dn = "CN=Alice,OU=Finance,DC=corp,DC=contoso,DC=com"
        enrichment = enrich_user(alice_dn, _FOREST[alice_dn], _FOREST, set())
        assert enrichment.candidate_orgpath is not None
        assert "FIN" in enrichment.candidate_orgpath

    def test_enrich_user_long_ou_name_returns_none(self) -> None:
        # "Baltimore" (9 chars) and "EastRegion" (10 chars) both exceed the
        # 6-char limit — _normalize_segment returns None, so no candidate OrgPath.
        dn = "CN=GeoUser,OU=Baltimore,OU=EastRegion,DC=corp,DC=contoso,DC=com"
        user_obj = {
            "object_class": "user",
            "sAMAccountName": "geouser",
            "userAccountControl": 512,
            "lastLogonTimestamp": _build_windows_filetime(5),
            "manager": None,
            "memberOf": [],
        }
        enrichment = enrich_user(dn, user_obj, _FOREST, set())
        assert enrichment.candidate_orgpath is None


# ===========================================================================
# Schema additive: existing keys preserved, new fields don't break as_dict
# ===========================================================================


class TestSchemaAdditive:
    """Verify ADSurveyReport.as_dict() keys are preserved (no breaking changes)."""

    _EXPECTED_KEYS = {
        "forest_root",
        "domain_count",
        "ou_total",
        "ou_functional",
        "ou_geographic_active",
        "ou_geographic_orphan",
        "ou_technical",
        "ou_delegation_artifact",
        "user_total",
        "user_hr_resolvable",
        "user_orgpath_derived",
        "user_unresolvable",
        "computer_total",
        "computer_stale",
        "sa_total",
        "sa_with_spn",
        "sa_adcs_dependent",
        "sa_orphaned",
        "gpo_total",
        "gpo_geographic_only",
        "gpo_no_live_intent",
        "site_total",
        "site_stale",
        "findings",
        "ok",
        "blocker_count",
    }

    def test_existing_keys_preserved(self) -> None:
        d = ADSurveyReport(forest_root=_BASE_DN).as_dict()
        for key in self._EXPECTED_KEYS:
            assert key in d, f"Missing pre-existing key: {key}"

    def test_user_enrichment_json_serialisable(self) -> None:
        """All UserEnrichment fields must be JSON-serialisable."""
        alice_dn = "CN=Alice,OU=Finance,DC=corp,DC=contoso,DC=com"
        enrichment = enrich_user(alice_dn, _FOREST[alice_dn], _FOREST, set())
        payload = {
            "distinguished_name": enrichment.distinguished_name,
            "sam_account_name": enrichment.sam_account_name,
            "account_flags": enrichment.account_flags.__dict__,
            "is_stale": enrichment.is_stale,
            "stale_days": enrichment.stale_days,
            "manager_chain": enrichment.manager_chain,
            "manager_chain_cycle": enrichment.manager_chain_cycle,
            "group_memberships": enrichment.group_memberships,
            "group_memberships_cycle": enrichment.group_memberships_cycle,
            "orphaned_sids": enrichment.orphaned_sids,
            "candidate_orgpath": enrichment.candidate_orgpath,
        }
        json.dumps(payload)  # must not raise
