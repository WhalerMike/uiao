"""Tests for the CQL `SHOW LINKS` domain (UIAO_108 + UIAO_145 / ADR-132).

Covers:
- Grammar: SHOW LINKS parses; unknown domains still fail
- Rows sourced from the canon registry via cql_link_rows()
- WHERE filtering on counterparty_class / provenance_anchored
- FOR CONTROL as membership in the link's bound controls
- ORDER BY determinism
- An engine with no links yields an empty result, not an error
"""

from __future__ import annotations

import pytest

from uiao.cql.engine import CQLEngine, CQLParseError, parse
from uiao.evidence.links import cql_link_rows


@pytest.fixture(scope="module")
def engine() -> CQLEngine:
    return CQLEngine(links=cql_link_rows())


def test_show_links_parses() -> None:
    q = parse("SHOW LINKS WHERE counterparty_class = 'federal-agency' ORDER BY id DESC")
    assert q.query_type == "LINKS"
    assert q.filters == [("counterparty_class", "=", "federal-agency")]
    assert q.order_by == "id"
    assert q.order_dir == "DESC"


def test_unknown_domain_still_fails() -> None:
    with pytest.raises(CQLParseError):
        parse("SHOW GADGETS")


def test_show_all_links(engine: CQLEngine) -> None:
    result = engine.execute("SHOW LINKS")
    assert result.query_type == "LINKS"
    assert result.total >= 5
    ids = [r["id"] for r in result.records]
    assert "sailpoint-nerm-nonemployee" in ids


def test_where_counterparty_class(engine: CQLEngine) -> None:
    result = engine.execute("SHOW LINKS WHERE counterparty_class = 'federal-agency'")
    assert result.total >= 4
    assert all(r["counterparty_class"] == "federal-agency" for r in result.records)


def test_where_provenance_anchored_false(engine: CQLEngine) -> None:
    result = engine.execute("SHOW LINKS WHERE provenance_anchored = 'false'")
    ids = {r["id"] for r in result.records}
    assert "federal-hrit-integration" not in ids
    assert "opm-apim-federal-gateway" in ids


def test_for_control_membership(engine: CQLEngine) -> None:
    result = engine.execute("SHOW LINKS FOR CONTROL 'SA-9'")
    ids = {r["id"] for r in result.records}
    assert ids == {"opm-apim-federal-gateway", "sailpoint-nerm-nonemployee"}


def test_order_by_id_deterministic(engine: CQLEngine) -> None:
    result = engine.execute("SHOW LINKS ORDER BY id ASC")
    ids = [r["id"] for r in result.records]
    assert ids == sorted(ids)


def test_engine_without_links_returns_empty() -> None:
    result = CQLEngine().execute("SHOW LINKS")
    assert result.total == 0
    assert result.records == []
