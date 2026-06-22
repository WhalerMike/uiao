"""Integration test: start the AGD server, query it with a real LDAP client.

Requires the [directory] extra (ldap3>=2.9).  Run with:

    pytest tests/directory/test_agd_integration.py -v

These tests prove Step 1A of the AGD in-path program: the LDAPv3 server
accepts connections, projects the OrgPath snapshot correctly over the wire,
and returns the right attributes to an LDAP client.  The fixture used is the
federal-agency snapshot (tests/fixtures/agd/federal-agency-snapshot.json).
"""

from __future__ import annotations

import asyncio
import json
import socket
import threading
import time
from pathlib import Path

import pytest

ldap3 = pytest.importorskip("ldap3", reason="[directory] extra required: pip install 'uiao[directory]'")

from uiao.directory import build_directory  # noqa: E402
from uiao.directory.server import LdapServer  # noqa: E402

FIXTURE = Path(__file__).parent.parent / "fixtures" / "agd" / "federal-agency-snapshot.json"
BASE_DN = "dc=agd,dc=uiao,dc=gov"


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def agd_server():
    """Start the AGD LDAPv3 server in a background thread; yield (host, port)."""
    snapshot = json.loads(FIXTURE.read_text(encoding="utf-8"))
    principals = snapshot["principals"]
    directory = build_directory(principals, base_dn=BASE_DN)
    server = LdapServer(
        directory=directory,
        credentials={"operator": "test-secret"},
    )

    port = _free_port()
    loop = asyncio.new_event_loop()

    def _run() -> None:
        asyncio.set_event_loop(loop)
        loop.run_until_complete(server.serve(host="127.0.0.1", port=port))

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    # Give the server a moment to bind.
    time.sleep(0.3)
    yield ("127.0.0.1", port)
    loop.call_soon_threadsafe(loop.stop)


def _connect(host: str, port: int, *, bind_dn: str = "", password: str = "") -> ldap3.Connection:
    server = ldap3.Server(host, port=port, get_info=ldap3.NONE)
    conn = ldap3.Connection(server, user=bind_dn, password=password, auto_bind=ldap3.AUTO_BIND_NO_TLS)
    conn.open()
    if bind_dn:
        conn.bind()
    return conn


# ---------------------------------------------------------------------------
# Anonymous search — root entry
# ---------------------------------------------------------------------------


class TestAnonymousSearch:
    def test_root_entry_returned(self, agd_server):
        host, port = agd_server
        conn = _connect(host, port)
        conn.search(BASE_DN, "(objectClass=*)", search_scope=ldap3.BASE, attributes=["dc"])
        assert any(BASE_DN in str(e.entry_dn) for e in conn.entries), conn.entries

    def test_subtree_returns_all_principals(self, agd_server):
        host, port = agd_server
        conn = _connect(host, port)
        conn.search(
            BASE_DN, "(objectClass=uiaoOrgPath)", search_scope=ldap3.SUBTREE, attributes=["cn", "uiaoPrincipalType"]
        )
        assert len(conn.entries) == 13, f"expected 13 principals, got {len(conn.entries)}"

    def test_user_count(self, agd_server):
        host, port = agd_server
        conn = _connect(host, port)
        conn.search(
            BASE_DN,
            "(&(objectClass=uiaoOrgPath)(uiaoPrincipalType=user))",
            search_scope=ldap3.SUBTREE,
            attributes=["cn"],
        )
        assert len(conn.entries) == 9

    def test_device_count(self, agd_server):
        host, port = agd_server
        conn = _connect(host, port)
        conn.search(
            BASE_DN,
            "(&(objectClass=uiaoOrgPath)(uiaoPrincipalType=device))",
            search_scope=ldap3.SUBTREE,
            attributes=["cn"],
        )
        assert len(conn.entries) == 2

    def test_service_principal_count(self, agd_server):
        host, port = agd_server
        conn = _connect(host, port)
        conn.search(
            BASE_DN,
            "(&(objectClass=uiaoOrgPath)(uiaoPrincipalType=servicePrincipal))",
            search_scope=ldap3.SUBTREE,
            attributes=["cn"],
        )
        assert len(conn.entries) == 2


# ---------------------------------------------------------------------------
# OrgPath facet values come back correctly
# ---------------------------------------------------------------------------


class TestFacetProjection:
    def _get(self, agd_server, cn_fragment: str) -> ldap3.Entry:
        host, port = agd_server
        conn = _connect(host, port)
        conn.search(
            BASE_DN,
            f"(cn=*{cn_fragment}*)",
            search_scope=ldap3.SUBTREE,
            attributes=["*"],
        )
        assert conn.entries, f"No entry matching cn=*{cn_fragment}*"
        return conn.entries[0]

    def test_architect_has_correct_region_and_placement(self, agd_server):
        """Non-sensitive facets available to anonymous bind."""
        e = self._get(agd_server, "m.stratton")
        assert str(e["uiaoOrgPathRegion"]) == "NCR"
        assert str(e["uiaoOrgPathDivision"]) == "Identity"
        assert str(e["uiaoOrgPathRole"]) == "Architect"
        assert str(e["uiaoOrgPathAccountType"]) == "Privileged"

    def test_clearance_level_requires_authenticated_bind(self, agd_server):
        """Sensitive facets (clearance) are only returned after authenticated bind (ADR-100 §5)."""
        host, port = agd_server
        # Anonymous — clearance should be absent or empty
        anon_conn = _connect(host, port)
        anon_conn.search(
            BASE_DN, "(cn=*m.stratton*)", search_scope=ldap3.SUBTREE, attributes=["uiaoOrgPathClearanceLevel"]
        )
        anon_entry = anon_conn.entries[0]
        assert not anon_entry["uiaoOrgPathClearanceLevel"].values, "clearance level must be redacted for anonymous bind"

        # Authenticated — clearance should be present
        auth_conn = _connect(host, port, bind_dn="operator", password="test-secret")
        auth_conn.search(
            BASE_DN, "(cn=*m.stratton*)", search_scope=ldap3.SUBTREE, attributes=["uiaoOrgPathClearanceLevel"]
        )
        auth_entry = auth_conn.entries[0]
        assert str(auth_entry["uiaoOrgPathClearanceLevel"]) == "TS_SCI", (
            "authenticated bind must return clearance level"
        )

    def test_contractor_has_term_date(self, agd_server):
        e = self._get(agd_server, "t.nguyen")
        assert str(e["uiaoOrgPathClassification"]) == "Contractor"
        assert str(e["uiaoOrgPathTermDate"]) == "2026-12-31"

    def test_ciso_is_executive(self, agd_server):
        e = self._get(agd_server, "ciso")
        assert str(e["uiaoOrgPathRole"]) == "CISO"
        assert str(e["uiaoOrgPathClassification"]) == "Executive"

    def test_service_principal_has_no_role_facet(self, agd_server):
        host, port = agd_server
        conn = _connect(host, port)
        conn.search(
            BASE_DN,
            "(cn=svc-ai-web-scanner)",
            search_scope=ldap3.SUBTREE,
            attributes=["uiaoOrgPathRole", "uiaoOrgPathAccountType"],
        )
        assert conn.entries
        e = conn.entries[0]
        assert str(e["uiaoOrgPathAccountType"]) == "Service"
        # Role facet is absent for servicePrincipals (no extensionAttribute4 set)
        assert not e["uiaoOrgPathRole"].values

    def test_remote_user_has_eastus_region(self, agd_server):
        e = self._get(agd_server, "k.ibrahim")
        assert str(e["uiaoOrgPathRegion"]) == "EASTUS"
        assert str(e["uiaoOrgPathDivision"]) == "InfraOps"


# ---------------------------------------------------------------------------
# Governance-relevant filtered queries — what SailPoint / ServiceNow would run
# ---------------------------------------------------------------------------


class TestGovernanceQueries:
    """These queries model what an IGA system (SailPoint ISC, ServiceNow) would
    issue to the AGD to make a provisioning or routing decision."""

    def test_query_all_privileged_accounts_in_cyberops(self, agd_server):
        """SailPoint access-review feed: privileged CyberOps users."""
        host, port = agd_server
        conn = _connect(host, port)
        conn.search(
            BASE_DN,
            "(&(uiaoOrgPathDivision=CyberOps)(uiaoOrgPathAccountType=Privileged))",
            search_scope=ldap3.SUBTREE,
            attributes=["cn", "uiaoOrgPathRole", "uiaoOrgPathClearanceLevel"],
        )
        # CISO and WKS-NCR-0101 are Privileged in CyberOps
        assert len(conn.entries) == 2
        cns = {str(e["cn"]) for e in conn.entries}
        assert "ciso@agency.gov" in cns

    def test_query_contractors_expiring_within_a_year(self, agd_server):
        """HR/IGA: flag contractors whose term_date is set (potential leavers)."""
        host, port = agd_server
        conn = _connect(host, port)
        conn.search(
            BASE_DN,
            "(&(uiaoOrgPathClassification=Contractor)(uiaoOrgPathTermDate=*))",
            search_scope=ldap3.SUBTREE,
            attributes=["cn", "uiaoOrgPathTermDate"],
        )
        assert len(conn.entries) == 1
        assert "t.nguyen" in str(conn.entries[0]["cn"])

    def test_query_all_service_accounts_for_rotation_audit(self, agd_server):
        """Security audit: list all service principals for credential rotation review."""
        host, port = agd_server
        conn = _connect(host, port)
        conn.search(
            BASE_DN,
            "(uiaoOrgPathAccountType=Service)",
            search_scope=ldap3.SUBTREE,
            attributes=["cn", "uiaoOrgPathDivision"],
        )
        assert len(conn.entries) == 2
        cns = {str(e["cn"]) for e in conn.entries}
        assert "svc-ai-web-scanner" in cns
        assert "svc-sentinel-ingest" in cns

    def test_query_tssci_users_for_access_review(self, agd_server):
        """Clearance-based access review: TS/SCI holders needing annual review."""
        host, port = agd_server
        conn = _connect(host, port)
        conn.search(
            BASE_DN,
            "(&(uiaoOrgPathClearanceLevel=TS_SCI)(uiaoPrincipalType=user))",
            search_scope=ldap3.SUBTREE,
            attributes=["cn", "uiaoOrgPathRole"],
        )
        assert len(conn.entries) == 2  # m.stratton (Architect) + ciso (CISO)

    def test_query_ncr_it_department_for_au_scoping(self, agd_server):
        """Entra AU scoping: NCR IT department members for Administrative Unit delegation."""
        host, port = agd_server
        conn = _connect(host, port)
        conn.search(
            BASE_DN,
            "(&(uiaoOrgPathRegion=NCR)(uiaoOrgPathDepartment=IT)(uiaoPrincipalType=user))",
            search_scope=ldap3.SUBTREE,
            attributes=["cn", "uiaoOrgPathDivision", "uiaoOrgPathRole"],
        )
        # NCR IT users: m.stratton, j.chen, r.okonkwo, d.vasquez, k.ibrahim(EASTUS-skip),
        #               ciso, t.nguyen.ctr — 6 users (k.ibrahim is EASTUS)
        assert len(conn.entries) == 6
