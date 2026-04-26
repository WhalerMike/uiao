"""Tests for UIAO_116 / §3.5 Enforcement Policy Language.

Covers vocabulary parsing, YAML policy loader, evaluator semantics
(wildcard fields / severity_min / drift_class / controls / adapter_ids
/ pillars / multi-match), OSCAL back-matter projection, and the
canonical-policy smoke against the ref policies shipped in
``src/uiao/canon/policies/``.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from uiao.governance.epl import (
    EPLAction,
    EPLContext,
    EPLEvaluator,
    EPLPolicy,
    EPLTrigger,
    back_matter_resources_for_policies,
    load_canonical_policies,
    load_policies,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _write_policy(path: Path, body: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(body), encoding="utf-8")
    return path


def _simple_policy(
    pid: str = "epl:test",
    drift_class: list[str] | None = None,
    controls: list[str] | None = None,
    severity_min: str = "",
    action: str = "alert",
) -> dict:
    return {
        "id": pid,
        "description": f"test policy {pid}",
        "when": {
            "drift_class": drift_class or [],
            "controls": controls or [],
            "severity_min": severity_min,
        },
        "then": {
            "action": action,
            "actor": "test-actor",
            "sla_hours": 12,
        },
    }


# ---------------------------------------------------------------------------
# Vocabulary
# ---------------------------------------------------------------------------


class TestEPLActionParse:
    def test_canonical(self):
        assert EPLAction.parse("alert") == EPLAction.ALERT
        assert EPLAction.parse("REMEDIATE") == EPLAction.REMEDIATE

    def test_unknown_returns_none(self):
        assert EPLAction.parse("phantom") is None
        assert EPLAction.parse("") is None
        assert EPLAction.parse(None) is None


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------


class TestLoadPolicies:
    def test_missing_files_return_empty(self, tmp_path):
        assert load_policies([tmp_path / "nope.yaml"]) == []

    def test_single_flat_policy(self, tmp_path):
        path = _write_policy(tmp_path / "p1.yaml", _simple_policy("epl:a"))
        policies = load_policies([path])
        assert len(policies) == 1
        assert policies[0].id == "epl:a"
        assert policies[0].action == EPLAction.ALERT
        assert policies[0].actor == "test-actor"
        assert policies[0].sla_hours == 12

    def test_top_level_policies_list(self, tmp_path):
        path = tmp_path / "p.yaml"
        path.write_text(
            yaml.safe_dump(
                {
                    "policies": [
                        _simple_policy("epl:a"),
                        _simple_policy("epl:b"),
                    ]
                }
            ),
            encoding="utf-8",
        )
        policies = load_policies([path])
        assert {p.id for p in policies} == {"epl:a", "epl:b"}

    def test_id_dedupe_keeps_last(self, tmp_path):
        a = _write_policy(tmp_path / "a.yaml", _simple_policy("epl:dup", action="alert"))
        b = _write_policy(tmp_path / "b.yaml", _simple_policy("epl:dup", action="block"))
        policies = load_policies([a, b])
        assert len(policies) == 1
        assert policies[0].action == EPLAction.BLOCK

    def test_invalid_yaml_skipped(self, tmp_path):
        path = tmp_path / "bad.yaml"
        path.write_text(":: not valid yaml ::", encoding="utf-8")
        assert load_policies([path]) == []

    def test_missing_id_dropped(self, tmp_path):
        path = tmp_path / "noid.yaml"
        path.write_text(
            yaml.safe_dump({"description": "no id here", "then": {"action": "log"}}),
            encoding="utf-8",
        )
        assert load_policies([path]) == []

    def test_unknown_action_falls_back_to_log(self, tmp_path):
        path = _write_policy(
            tmp_path / "u.yaml",
            {
                "id": "epl:unknown-action",
                "then": {"action": "phantom"},
            },
        )
        policies = load_policies([path])
        assert policies[0].action == EPLAction.LOG


# ---------------------------------------------------------------------------
# Evaluator semantics
# ---------------------------------------------------------------------------


class TestEvaluator:
    def test_empty_when_matches_anything(self):
        p = EPLPolicy(id="epl:wildcard", when=EPLTrigger())
        e = EPLEvaluator(policies=[p])
        ctx = EPLContext(drift_class="DRIFT-AUTHZ")
        assert len(e.evaluate(ctx)) == 1

    def test_drift_class_filter(self, tmp_path):
        path = _write_policy(
            tmp_path / "p.yaml",
            _simple_policy("epl:a", drift_class=["DRIFT-AUTHZ"]),
        )
        e = EPLEvaluator(policies=load_policies([path]))
        assert e.evaluate(EPLContext(drift_class="DRIFT-AUTHZ"))
        assert not e.evaluate(EPLContext(drift_class="DRIFT-IDENTITY"))

    def test_controls_intersection(self, tmp_path):
        path = _write_policy(
            tmp_path / "p.yaml",
            _simple_policy("epl:a", controls=["IA-2", "IA-2.1"]),
        )
        e = EPLEvaluator(policies=load_policies([path]))
        # Match: ctx names IA-2.
        assert e.evaluate(EPLContext(controls=frozenset({"IA-2"})))
        # No match: ctx control disjoint from policy controls.
        assert not e.evaluate(EPLContext(controls=frozenset({"AC-2"})))
        # No match: ctx has no control at all.
        assert not e.evaluate(EPLContext())

    def test_severity_min(self, tmp_path):
        path = _write_policy(
            tmp_path / "p.yaml",
            _simple_policy("epl:a", severity_min="Medium"),
        )
        e = EPLEvaluator(policies=load_policies([path]))
        assert e.evaluate(EPLContext(severity="High"))
        assert e.evaluate(EPLContext(severity="Medium"))
        assert not e.evaluate(EPLContext(severity="Low"))
        # P-vocabulary maps onto the same ordinal scale.
        assert e.evaluate(EPLContext(severity="P1"))
        assert not e.evaluate(EPLContext(severity="P5"))

    def test_adapter_ids_filter(self):
        p = EPLPolicy(id="epl:a", when=EPLTrigger(adapter_ids=frozenset({"entra-id"})))
        e = EPLEvaluator(policies=[p])
        assert e.evaluate(EPLContext(adapter_id="entra-id"))
        assert not e.evaluate(EPLContext(adapter_id="m365"))

    def test_pillars_intersection(self):
        p = EPLPolicy(
            id="epl:a",
            when=EPLTrigger(pillars=frozenset({"identity"})),
        )
        e = EPLEvaluator(policies=[p])
        assert e.evaluate(EPLContext(pillars=frozenset({"identity", "data"})))
        assert not e.evaluate(EPLContext(pillars=frozenset({"data"})))

    def test_multi_match_id_sorted(self):
        p1 = EPLPolicy(id="epl:b-second", when=EPLTrigger(drift_class=frozenset({"DRIFT-AUTHZ"})))
        p2 = EPLPolicy(id="epl:a-first", when=EPLTrigger(drift_class=frozenset({"DRIFT-AUTHZ"})))
        e = EPLEvaluator(policies=[p1, p2])
        matches = e.evaluate(EPLContext(drift_class="DRIFT-AUTHZ"))
        assert [m.policy.id for m in matches] == ["epl:a-first", "epl:b-second"]


# ---------------------------------------------------------------------------
# Context builders
# ---------------------------------------------------------------------------


class TestContextBuilders:
    def test_from_drift_state(self):
        class DS:
            drift_class = "DRIFT-AUTHZ"
            policy_ref = "AC-2"
            classification = "unauthorized"

        ctx = EPLContext.from_drift_state(DS())
        assert ctx.drift_class == "DRIFT-AUTHZ"
        assert "AC-2" in ctx.controls
        assert ctx.severity == "unauthorized"

    def test_from_finding(self):
        class F:
            drift_class = "DRIFT-IDENTITY"
            control_id = "IA-2"
            severity = "High"
            extra = {"adapter_id": "entra-id"}

        ctx = EPLContext.from_finding(F())
        assert ctx.drift_class == "DRIFT-IDENTITY"
        assert ctx.controls == frozenset({"IA-2"})
        assert ctx.adapter_id == "entra-id"
        assert ctx.severity == "High"

    def test_evaluate_drift_state_round_trip(self):
        class DS:
            drift_class = "DRIFT-AUTHZ"
            policy_ref = ""
            classification = "unauthorized"

        p = EPLPolicy(id="epl:t", when=EPLTrigger(drift_class=frozenset({"DRIFT-AUTHZ"})))
        e = EPLEvaluator(policies=[p])
        assert len(e.evaluate_drift_state(DS())) == 1


# ---------------------------------------------------------------------------
# OSCAL back-matter projection
# ---------------------------------------------------------------------------


class TestBackMatterProjection:
    def test_one_resource_per_policy(self):
        policies = [
            EPLPolicy(
                id="epl:a",
                action=EPLAction.ALERT,
                actor="soc",
                sla_hours=24,
                when=EPLTrigger(drift_class=frozenset({"DRIFT-AUTHZ"})),
            ),
            EPLPolicy(id="epl:b", action=EPLAction.LOG),
        ]
        resources = back_matter_resources_for_policies(policies)
        assert len(resources) == 2
        ids = {next(p["value"] for p in r["props"] if p["name"] == "epl-policy-id") for r in resources}
        assert ids == {"epl:a", "epl:b"}

    def test_resource_uuid_deterministic(self):
        p = EPLPolicy(id="epl:stable")
        a = back_matter_resources_for_policies([p])
        b = back_matter_resources_for_policies([p])
        assert a[0]["uuid"] == b[0]["uuid"]

    def test_namespace_consistent(self):
        p = EPLPolicy(
            id="epl:a",
            actor="x",
            sla_hours=1,
            when=EPLTrigger(drift_class=frozenset({"DRIFT-AUTHZ"})),
        )
        resources = back_matter_resources_for_policies([p])
        for prop in resources[0]["props"]:
            assert prop["ns"] == "https://uiao.gov/ns/oscal/epl"

    def test_props_carry_trigger_predicate(self):
        p = EPLPolicy(
            id="epl:rich",
            when=EPLTrigger(
                drift_class=frozenset({"DRIFT-AUTHZ"}),
                controls=frozenset({"AC-2"}),
                adapter_ids=frozenset({"entra-id"}),
                pillars=frozenset({"identity"}),
                severity_min="Medium",
            ),
            action=EPLAction.BLOCK,
        )
        resources = back_matter_resources_for_policies([p])
        names = {prop["name"] for prop in resources[0]["props"]}
        assert "epl-when-drift-class" in names
        assert "epl-when-control" in names
        assert "epl-when-adapter" in names
        assert "epl-when-pillar" in names
        assert "epl-when-severity-min" in names

    def test_round_trips_through_json(self):
        p = EPLPolicy(id="epl:a")
        json.loads(json.dumps(back_matter_resources_for_policies([p])))


# ---------------------------------------------------------------------------
# Canonical reference policies smoke
# ---------------------------------------------------------------------------


class TestCanonicalPolicies:
    def test_canonical_dir_loads_all_reference_policies(self):
        policies = load_canonical_policies()
        ids = {p.id for p in policies}
        # The five reference policies shipped in this PR.
        expected = {
            "epl:enforce-mfa",
            "epl:block-out-of-scope",
            "epl:escalate-stale-evidence",
            "epl:fix-broken-issuer-chain",
            "epl:audit-schema-drift",
        }
        assert expected.issubset(ids), f"missing canonical policies: {expected - ids}"

    def test_enforce_mfa_matches_realistic_finding(self):
        e = EPLEvaluator(policies=load_canonical_policies())

        class F:
            drift_class = "DRIFT-SEMANTIC"
            control_id = "IA-2"
            severity = "High"
            extra = {"adapter_id": "entra-id"}

        matches = e.evaluate_finding(F())
        ids = {m.policy.id for m in matches}
        assert "epl:enforce-mfa" in ids
        assert "epl:escalate-stale-evidence" in ids

    def test_block_out_of_scope_matches_authz(self):
        e = EPLEvaluator(policies=load_canonical_policies())

        class DS:
            drift_class = "DRIFT-AUTHZ"
            policy_ref = ""
            classification = "unauthorized"

        matches = e.evaluate_drift_state(DS())
        ids = {m.policy.id for m in matches}
        assert "epl:block-out-of-scope" in ids
        # The block policy's action surfaces correctly.
        block = next(m for m in matches if m.policy.id == "epl:block-out-of-scope")
        assert block.policy.action == EPLAction.BLOCK

    def test_no_match_against_unrelated_finding(self):
        """A bare info-severity provenance finding should match nothing
        in the canonical set today (only audit-schema-drift requires
        DRIFT-SCHEMA, severity_min=Medium)."""
        e = EPLEvaluator(policies=load_canonical_policies())

        class F:
            drift_class = "DRIFT-PROVENANCE"
            control_id = ""
            severity = "Low"
            extra = {}

        assert e.evaluate_finding(F()) == []

    def test_canonical_policies_have_actor_and_sla(self):
        """Canon-shipping policies should always declare actor + sla_hours."""
        for p in load_canonical_policies():
            assert p.actor, f"{p.id} missing actor"
            assert p.sla_hours >= 0
