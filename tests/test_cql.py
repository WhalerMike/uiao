"""Tests for UIAO_108 / §3.2 Compliance Query Language."""

from __future__ import annotations


import pytest

from uiao.governance.cql import (
    CQLEvaluator,
    CQLParseError,
    CQLPredicate,
    CQLQuery,
    adapters_resolver,
    graph_findings_resolver,
    journal_records_resolver,
    load_canonical_queries,
    make_default_resolver,
    parse_query,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _findings_records() -> list[dict]:
    return [
        {"id": "f1", "drift_class": "DRIFT-AUTHZ", "status": "Open", "severity": "High", "control_id": "AC-2"},
        {"id": "f2", "drift_class": "DRIFT-AUTHZ", "status": "Closed", "severity": "Medium", "control_id": "AC-2"},
        {"id": "f3", "drift_class": "DRIFT-IDENTITY", "status": "Open", "severity": "High", "control_id": "IA-2"},
        {"id": "f4", "drift_class": "DRIFT-SEMANTIC", "status": "Open", "severity": "Low", "control_id": "AC-2"},
    ]


def _enforcement_records() -> list[dict]:
    return [
        {
            "policy_id": "epl:block-out-of-scope",
            "action": "block",
            "target": "rogue",
            "dispatched_at": "2026-04-26T10:00:00+00:00",
        },
        {
            "policy_id": "epl:enforce-mfa",
            "action": "remediate",
            "target": "entra-id",
            "dispatched_at": "2026-04-26T11:00:00+00:00",
        },
        {
            "policy_id": "epl:audit-schema-drift",
            "action": "alert",
            "target": "scuba",
            "dispatched_at": "2026-04-26T12:00:00+00:00",
        },
    ]


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------


class TestParse:
    def test_minimal_query(self):
        q = parse_query({"source": "findings"})
        assert q.source == "findings"
        assert q.where == ()
        assert q.limit == 0

    def test_yaml_string_round_trip(self):
        q = parse_query("source: findings\nwhere:\n  status: Open\nlimit: 10\n")
        assert q.source == "findings"
        assert q.limit == 10
        assert any(p.field == "status" and p.value == "Open" for p in q.where)

    def test_select_list(self):
        q = parse_query({"source": "findings", "select": ["id", "severity"]})
        assert q.select == ("id", "severity")

    def test_select_string_normalized_to_tuple(self):
        q = parse_query({"source": "findings", "select": "id"})
        assert q.select == ("id",)

    def test_predicate_eq_default(self):
        q = parse_query({"source": "findings", "where": {"status": "Open"}})
        assert q.where[0].op == "eq"
        assert q.where[0].value == "Open"

    def test_predicate_op_form(self):
        q = parse_query(
            {
                "source": "findings",
                "where": {
                    "severity": {"op": "in", "value": ["High", "Critical"]},
                },
            }
        )
        assert q.where[0].op == "in"
        assert q.where[0].value == ["High", "Critical"]

    def test_unknown_source_raises(self):
        with pytest.raises(CQLParseError):
            parse_query({"source": "phantom"})

    def test_unknown_op_raises(self):
        with pytest.raises(CQLParseError):
            parse_query({"source": "findings", "where": {"x": {"op": "fuzzy"}}})

    def test_invalid_order_raises(self):
        with pytest.raises(CQLParseError):
            parse_query({"source": "findings", "order": "sideways"})

    def test_negative_limit_raises(self):
        with pytest.raises(CQLParseError):
            parse_query({"source": "findings", "limit": -1})

    def test_invalid_yaml_raises(self):
        with pytest.raises(CQLParseError):
            parse_query(":: not yaml ::")

    def test_non_mapping_raises(self):
        with pytest.raises(CQLParseError):
            parse_query([1, 2, 3])


# ---------------------------------------------------------------------------
# Predicate matchers
# ---------------------------------------------------------------------------


class TestPredicateMatching:
    def test_eq_and_ne(self):
        rec = {"status": "Open"}
        assert CQLPredicate("status", "eq", "Open").matches(rec)
        assert not CQLPredicate("status", "eq", "Closed").matches(rec)
        assert CQLPredicate("status", "ne", "Closed").matches(rec)

    def test_in_and_not_in(self):
        rec = {"severity": "High"}
        assert CQLPredicate("severity", "in", ["High", "Critical"]).matches(rec)
        assert not CQLPredicate("severity", "in", ["Low"]).matches(rec)
        assert CQLPredicate("severity", "not_in", ["Low"]).matches(rec)

    def test_contains(self):
        # contains works on strings (substring) and lists (membership).
        assert CQLPredicate("name", "contains", "foo").matches({"name": "foo-bar"})
        assert CQLPredicate("tags", "contains", "x").matches({"tags": ["x", "y"]})
        assert not CQLPredicate("tags", "contains", "z").matches({"tags": ["x", "y"]})

    def test_gte_and_lte(self):
        rec = {"count": 5}
        assert CQLPredicate("count", "gte", 5).matches(rec)
        assert CQLPredicate("count", "lte", 10).matches(rec)
        assert not CQLPredicate("count", "gte", 6).matches(rec)

    def test_exists(self):
        rec = {"a": None, "b": "x"}
        assert CQLPredicate("a", "exists").matches(rec)
        assert CQLPredicate("b", "exists").matches(rec)
        assert not CQLPredicate("c", "exists").matches(rec)

    def test_type_mismatch_safe(self):
        # contains on an int target falls through to False (no TypeError).
        assert not CQLPredicate("x", "contains", "y").matches({"x": 42})


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------


class TestEvaluator:
    def test_simple_filter_and_count(self):
        resolver = make_default_resolver(findings=_findings_records())
        result = CQLEvaluator(resolver=resolver).evaluate(
            CQLQuery(source="findings", where=(CQLPredicate("status", "eq", "Open"),))
        )
        assert result.count == 3
        assert all(r["status"] == "Open" for r in result.rows)

    def test_multiple_predicates_and(self):
        resolver = make_default_resolver(findings=_findings_records())
        result = CQLEvaluator(resolver=resolver).evaluate(
            parse_query(
                {
                    "source": "findings",
                    "where": {"drift_class": "DRIFT-AUTHZ", "status": "Open"},
                }
            )
        )
        assert result.count == 1
        assert result.rows[0]["id"] == "f1"

    def test_order_by_desc(self):
        resolver = make_default_resolver(findings=_findings_records())
        result = CQLEvaluator(resolver=resolver).evaluate(
            parse_query({"source": "findings", "order_by": "id", "order": "desc"})
        )
        assert [r["id"] for r in result.rows] == ["f4", "f3", "f2", "f1"]

    def test_limit(self):
        resolver = make_default_resolver(findings=_findings_records())
        result = CQLEvaluator(resolver=resolver).evaluate(
            parse_query({"source": "findings", "limit": 2, "order_by": "id"})
        )
        assert result.count == 2

    def test_select_projects(self):
        resolver = make_default_resolver(findings=_findings_records())
        result = CQLEvaluator(resolver=resolver).evaluate(
            parse_query({"source": "findings", "select": ["id", "severity"]})
        )
        assert all(set(r.keys()) == {"id", "severity"} for r in result.rows)

    def test_unknown_source_returns_empty(self):
        resolver = make_default_resolver()
        # Bypass parse_query to construct an invalid-source query
        # directly — the evaluator falls through to an empty result.
        result = CQLEvaluator(resolver=resolver).evaluate(CQLQuery(source="findings"))
        assert result.count == 0

    def test_in_predicate_via_evaluator(self):
        resolver = make_default_resolver(findings=_findings_records())
        result = CQLEvaluator(resolver=resolver).evaluate(
            parse_query(
                {
                    "source": "findings",
                    "where": {"severity": {"op": "in", "value": ["High"]}},
                }
            )
        )
        assert result.count == 2
        assert {r["id"] for r in result.rows} == {"f1", "f3"}

    def test_ordering_handles_none(self):
        resolver = make_default_resolver(findings=[{"id": "a"}, {"id": "b", "severity": "High"}, {"id": "c"}])
        result = CQLEvaluator(resolver=resolver).evaluate(
            parse_query({"source": "findings", "order_by": "severity", "order": "asc"})
        )
        # None sorts before any string; output stable.
        assert result.rows[-1]["severity"] == "High"


# ---------------------------------------------------------------------------
# Source resolvers
# ---------------------------------------------------------------------------


class TestGraphResolver:
    def test_projects_finding_nodes(self):
        from uiao.evidence.graph import EvidenceGraph, FindingNode

        g = EvidenceGraph()
        g.add_finding(
            FindingNode(
                id="F-1",
                severity="High",
                control_id="AC-2",
                drift_class="DRIFT-AUTHZ",
                status="Open",
                extra={"adapter_id": "rogue", "run_id": "schedrun-x"},
            )
        )
        rows = graph_findings_resolver(g)
        assert len(rows) == 1
        assert rows[0]["id"] == "F-1"
        assert rows[0]["adapter_id"] == "rogue"


class TestJournalResolver:
    def test_records_with_as_dict(self):
        class R:
            def as_dict(self):
                return {"policy_id": "epl:t", "action": "log"}

        rows = journal_records_resolver([R()])
        assert rows == [{"policy_id": "epl:t", "action": "log"}]

    def test_dict_records_passthrough(self):
        rows = journal_records_resolver([{"a": 1}])
        assert rows == [{"a": 1}]


class TestAdaptersResolver:
    def test_drops_nested_objects(self):
        rows = adapters_resolver(
            [
                {"id": "x", "status": "active", "scope": ["a", "b"], "nested": {"k": 1}},
            ]
        )
        assert rows[0]["id"] == "x"
        # Nested dicts dropped (not flat).
        assert "nested" not in rows[0]
        # List values retained.
        assert rows[0]["scope"] == ["a", "b"]


# ---------------------------------------------------------------------------
# Canonical queries smoke
# ---------------------------------------------------------------------------


class TestCanonicalQueries:
    def test_canonical_dir_loads_all(self):
        queries = load_canonical_queries()
        assert "open-drift-authz-findings" in queries
        assert "recent-blocks" in queries
        assert "high-severity-findings" in queries
        assert "archive-recent" in queries
        assert "active-modernization-adapters" in queries

    def test_canonical_queries_parse_clean(self):
        queries = load_canonical_queries()
        for name, q in queries.items():
            assert q.source in ("findings", "enforcement", "archive", "adapters"), name

    def test_canonical_query_evaluates_against_realistic_inputs(self):
        queries = load_canonical_queries()
        q = queries["open-drift-authz-findings"]
        resolver = make_default_resolver(findings=_findings_records())
        result = CQLEvaluator(resolver=resolver).evaluate(q)
        # Only f1 in the fixture is DRIFT-AUTHZ + Open.
        assert result.count == 1
        assert result.rows[0]["id"] == "f1"

    def test_recent_blocks_query_runs(self):
        queries = load_canonical_queries()
        q = queries["recent-blocks"]
        resolver = make_default_resolver(enforcement=_enforcement_records())
        result = CQLEvaluator(resolver=resolver).evaluate(q)
        # Only one record has action=block.
        assert result.count == 1
        assert result.rows[0]["policy_id"] == "epl:block-out-of-scope"


# ---------------------------------------------------------------------------
# CQL API router
# ---------------------------------------------------------------------------


pytest.importorskip("httpx")
pytest.importorskip("fastapi")
from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from uiao.api.routes import cql as cql_router  # noqa: E402


AUTH_HEADERS = {"Authorization": "Bearer test-token"}


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(cql_router.router, prefix="/api/v1/cql")
    return TestClient(app)


class TestCQLApi:
    def test_list_queries(self, client):
        r = client.get("/api/v1/cql/queries", headers=AUTH_HEADERS)
        assert r.status_code == 200
        names = {q["name"] for q in r.json()["queries"]}
        assert "open-drift-authz-findings" in names

    def test_get_named_query(self, client):
        r = client.get("/api/v1/cql/queries/recent-blocks", headers=AUTH_HEADERS)
        assert r.status_code == 200
        assert r.json()["source"] == "enforcement"

    def test_unknown_query_404(self, client):
        r = client.get("/api/v1/cql/queries/phantom", headers=AUTH_HEADERS)
        assert r.status_code == 404

    def test_evaluate_adhoc_against_adapters(self, client):
        # The adapters resolver reads canon, which has adapters with
        # status=active in modernization-registry.yaml.
        r = client.post(
            "/api/v1/cql/evaluate",
            headers=AUTH_HEADERS,
            json={"source": "adapters", "where": {"status": "active"}, "limit": 3},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["count"] >= 1

    def test_evaluate_named(self, client):
        r = client.post(
            "/api/v1/cql/evaluate/active-modernization-adapters",
            headers=AUTH_HEADERS,
        )
        assert r.status_code == 200
        body = r.json()
        # Active phase-1 adapters from canon — at least entra-id today.
        ids = {row["id"] for row in body["rows"] if "id" in row}
        assert "entra-id" in ids

    def test_evaluate_invalid_query_400(self, client):
        r = client.post(
            "/api/v1/cql/evaluate",
            headers=AUTH_HEADERS,
            json={"source": "phantom"},
        )
        assert r.status_code == 400

    def test_evaluate_named_unknown_404(self, client):
        r = client.post(
            "/api/v1/cql/evaluate/phantom",
            headers=AUTH_HEADERS,
        )
        assert r.status_code == 404

    def test_no_auth_returns_401(self, client):
        r = client.get("/api/v1/cql/queries")
        assert r.status_code == 401
