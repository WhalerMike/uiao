"""Tests for UIAO_120 / §3.6 ZTMM Integration.

Covers the ZTMMPillar / ZTMMMaturity vocabulary, registry loader,
score calculator (with and without an EvidenceGraph), OSCAL back-matter
projection, and the substrate-walker pillar-hygiene scan.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from uiao.evidence.graph import (
    ControlNode,
    EvidenceGraph,
    EvidenceNode,
    FindingNode,
)
from uiao.governance.ztmm import (
    AdapterZTMMDeclaration,
    ZTMMMaturity,
    ZTMMPillar,
    ZTMMScoreCalculator,
    back_matter_resources_for_report,
    load_ztmm_declarations,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _write_registry(path: Path, adapters: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump({"adapters": adapters}), encoding="utf-8")
    return path


def _graph_with_evidence(
    *,
    adapters: list[str],
    open_finding_for: list[str] | None = None,
) -> EvidenceGraph:
    """Build a graph where each named adapter has one EvidenceNode whose
    source matches its id. Optionally attach an Open finding tagged with
    a given adapter via extra.adapter_id."""
    g = EvidenceGraph()
    g.add_control(ControlNode(id="AC-2"))
    open_for = set(open_finding_for or [])
    for aid in adapters:
        g.add_evidence(
            EvidenceNode(
                id=f"EV-{aid}",
                source=aid,
                control_id="AC-2",
                hash="probe",
            )
        )
    for aid in open_for:
        g.add_finding(
            FindingNode(
                id=f"F-{aid}",
                severity="High",
                control_id="AC-2",
                status="Open",
                extra={"adapter_id": aid},
            )
        )
    return g


# ---------------------------------------------------------------------------
# Vocabulary
# ---------------------------------------------------------------------------


class TestZTMMPillarParse:
    def test_canonical_kebab(self):
        assert ZTMMPillar.parse("identity") == ZTMMPillar.IDENTITY
        assert ZTMMPillar.parse("applications-and-workloads") == ZTMMPillar.APPLICATIONS_AND_WORKLOADS

    def test_synonyms(self):
        assert ZTMMPillar.parse("apps") == ZTMMPillar.APPLICATIONS_AND_WORKLOADS
        assert ZTMMPillar.parse("workloads") == ZTMMPillar.APPLICATIONS_AND_WORKLOADS
        assert ZTMMPillar.parse("endpoints") == ZTMMPillar.DEVICES
        assert ZTMMPillar.parse("network") == ZTMMPillar.NETWORKS

    def test_unknown_returns_none(self):
        assert ZTMMPillar.parse("phantom") is None

    def test_empty_returns_none(self):
        assert ZTMMPillar.parse("") is None
        assert ZTMMPillar.parse(None) is None


class TestZTMMMaturityRank:
    def test_rank_ordering(self):
        assert ZTMMMaturity.TRADITIONAL.rank < ZTMMMaturity.INITIAL.rank
        assert ZTMMMaturity.INITIAL.rank < ZTMMMaturity.ADVANCED.rank
        assert ZTMMMaturity.ADVANCED.rank < ZTMMMaturity.OPTIMAL.rank


# ---------------------------------------------------------------------------
# Registry loader
# ---------------------------------------------------------------------------


class TestLoadZTMMDeclarations:
    def test_missing_files_return_empty(self, tmp_path):
        assert load_ztmm_declarations([tmp_path / "nope.yaml"]) == {}

    def test_simple_load(self, tmp_path):
        path = _write_registry(
            tmp_path / "r.yaml",
            [{"id": "entra-id", "ztmm-pillars": ["identity", "devices"]}],
        )
        decls = load_ztmm_declarations([path])
        assert decls["entra-id"].pillars == frozenset({ZTMMPillar.IDENTITY, ZTMMPillar.DEVICES})

    def test_explicit_empty_list_yields_empty_declaration(self, tmp_path):
        path = _write_registry(
            tmp_path / "r.yaml",
            [{"id": "info-only", "ztmm-pillars": []}],
        )
        decls = load_ztmm_declarations([path])
        assert "info-only" in decls
        assert decls["info-only"].pillars == frozenset()
        assert decls["info-only"].declared is False

    def test_unknown_pillar_dropped(self, tmp_path):
        path = _write_registry(
            tmp_path / "r.yaml",
            [{"id": "x", "ztmm-pillars": ["identity", "phantom-pillar"]}],
        )
        decls = load_ztmm_declarations([path])
        assert decls["x"].pillars == frozenset({ZTMMPillar.IDENTITY})

    def test_synonym_normalization(self, tmp_path):
        path = _write_registry(
            tmp_path / "r.yaml",
            [{"id": "y", "ztmm-pillars": ["apps", "endpoints"]}],
        )
        decls = load_ztmm_declarations([path])
        assert decls["y"].pillars == frozenset({ZTMMPillar.APPLICATIONS_AND_WORKLOADS, ZTMMPillar.DEVICES})

    def test_later_registry_overrides_earlier(self, tmp_path):
        a = _write_registry(tmp_path / "a.yaml", [{"id": "x", "ztmm-pillars": ["identity"]}])
        b = _write_registry(tmp_path / "b.yaml", [{"id": "x", "ztmm-pillars": ["data"]}])
        decls = load_ztmm_declarations([a, b])
        assert decls["x"].pillars == frozenset({ZTMMPillar.DATA})

    def test_adapters_without_key_dropped(self, tmp_path):
        path = _write_registry(tmp_path / "r.yaml", [{"id": "skinny"}])
        assert "skinny" not in load_ztmm_declarations([path])

    def test_modernization_top_level_key(self, tmp_path):
        path = tmp_path / "mod.yaml"
        path.write_text(
            yaml.safe_dump({"modernization_adapters": [{"id": "tf", "ztmm-pillars": ["networks"]}]}),
            encoding="utf-8",
        )
        decls = load_ztmm_declarations([path])
        assert decls["tf"].pillars == frozenset({ZTMMPillar.NETWORKS})


# ---------------------------------------------------------------------------
# Score calculator
# ---------------------------------------------------------------------------


class TestZTMMScoreCalculator:
    def test_traditional_when_no_declarations(self):
        calc = ZTMMScoreCalculator(declarations={})
        report = calc.score()
        for pillar in ZTMMPillar:
            assert report.scores[pillar].maturity == ZTMMMaturity.TRADITIONAL

    def test_initial_with_one_declaration(self):
        calc = ZTMMScoreCalculator(
            declarations={"a": AdapterZTMMDeclaration(adapter_id="a", pillars=frozenset({ZTMMPillar.IDENTITY}))}
        )
        report = calc.score()
        assert report.scores[ZTMMPillar.IDENTITY].maturity == ZTMMMaturity.INITIAL
        assert report.scores[ZTMMPillar.DEVICES].maturity == ZTMMMaturity.TRADITIONAL

    def test_advanced_requires_two_declared_plus_evidence(self):
        decls = {
            aid: AdapterZTMMDeclaration(adapter_id=aid, pillars=frozenset({ZTMMPillar.IDENTITY})) for aid in ("a", "b")
        }
        calc = ZTMMScoreCalculator(declarations=decls)
        # Without a graph, two declarations remain INITIAL.
        assert calc.score().scores[ZTMMPillar.IDENTITY].maturity == ZTMMMaturity.INITIAL
        # With evidence from one of the two adapters, ADVANCED.
        graph = _graph_with_evidence(adapters=["a"])
        score = calc.score(graph=graph).scores[ZTMMPillar.IDENTITY]
        assert score.maturity == ZTMMMaturity.ADVANCED
        assert score.evidenced_adapters == ("a",)

    def test_optimal_requires_three_plus_all_fresh(self):
        decls = {
            aid: AdapterZTMMDeclaration(adapter_id=aid, pillars=frozenset({ZTMMPillar.IDENTITY}))
            for aid in ("a", "b", "c")
        }
        calc = ZTMMScoreCalculator(declarations=decls)
        # All three have evidence and no Open finding → OPTIMAL.
        graph = _graph_with_evidence(adapters=["a", "b", "c"])
        score = calc.score(graph=graph).scores[ZTMMPillar.IDENTITY]
        assert score.maturity == ZTMMMaturity.OPTIMAL
        assert score.fresh_adapters == ("a", "b", "c")

    def test_optimal_demoted_to_advanced_with_open_finding(self):
        decls = {
            aid: AdapterZTMMDeclaration(adapter_id=aid, pillars=frozenset({ZTMMPillar.IDENTITY}))
            for aid in ("a", "b", "c")
        }
        calc = ZTMMScoreCalculator(declarations=decls)
        graph = _graph_with_evidence(adapters=["a", "b", "c"], open_finding_for=["b"])
        score = calc.score(graph=graph).scores[ZTMMPillar.IDENTITY]
        # b has an open finding → not all fresh → falls back to ADVANCED.
        assert score.maturity == ZTMMMaturity.ADVANCED
        assert "b" not in score.fresh_adapters

    def test_pillar_attribution_independent(self):
        decls = {
            "id-a": AdapterZTMMDeclaration(adapter_id="id-a", pillars=frozenset({ZTMMPillar.IDENTITY})),
            "net-a": AdapterZTMMDeclaration(adapter_id="net-a", pillars=frozenset({ZTMMPillar.NETWORKS})),
        }
        calc = ZTMMScoreCalculator(declarations=decls)
        report = calc.score()
        assert report.scores[ZTMMPillar.IDENTITY].declared_adapters == ("id-a",)
        assert report.scores[ZTMMPillar.NETWORKS].declared_adapters == ("net-a",)
        assert report.scores[ZTMMPillar.DATA].maturity == ZTMMMaturity.TRADITIONAL

    def test_overall_rank_average(self):
        decls = {
            "a": AdapterZTMMDeclaration(
                adapter_id="a",
                pillars=frozenset({ZTMMPillar.IDENTITY, ZTMMPillar.DEVICES}),
            )
        }
        calc = ZTMMScoreCalculator(declarations=decls)
        report = calc.score()
        # Two pillars at INITIAL (rank 1), three at TRADITIONAL (rank 0)
        # → average 2/5 = 0.4
        assert abs(report.overall_rank - 0.4) < 1e-9

    def test_report_as_dict_round_trips_through_json(self):
        decls = {"a": AdapterZTMMDeclaration(adapter_id="a", pillars=frozenset({ZTMMPillar.IDENTITY}))}
        calc = ZTMMScoreCalculator(declarations=decls)
        report = calc.score()
        d = report.as_dict()
        json.loads(json.dumps(d))  # round-trips


# ---------------------------------------------------------------------------
# OSCAL back-matter projection
# ---------------------------------------------------------------------------


class TestBackMatterProjection:
    def test_one_resource_per_pillar(self):
        decls = {"a": AdapterZTMMDeclaration(adapter_id="a", pillars=frozenset({ZTMMPillar.IDENTITY}))}
        report = ZTMMScoreCalculator(declarations=decls).score()
        resources = back_matter_resources_for_report(report)
        assert len(resources) == 5  # one per pillar
        for r in resources:
            assert "uuid" in r
            assert any(p["name"] == "ztmm-pillar" for p in r["props"])

    def test_resource_uuid_deterministic(self):
        decls = {"a": AdapterZTMMDeclaration(adapter_id="a", pillars=frozenset({ZTMMPillar.IDENTITY}))}
        r1 = back_matter_resources_for_report(ZTMMScoreCalculator(declarations=decls).score())
        r2 = back_matter_resources_for_report(ZTMMScoreCalculator(declarations=decls).score())
        for a, b in zip(r1, r2, strict=True):
            assert a["uuid"] == b["uuid"]

    def test_resource_props_include_declared_adapters(self):
        decls = {
            aid: AdapterZTMMDeclaration(adapter_id=aid, pillars=frozenset({ZTMMPillar.IDENTITY})) for aid in ("a", "b")
        }
        report = ZTMMScoreCalculator(declarations=decls).score()
        resources = back_matter_resources_for_report(report)
        identity_res = next(
            r for r in resources if any(p["name"] == "ztmm-pillar" and p["value"] == "identity" for p in r["props"])
        )
        names = {p["value"] for p in identity_res["props"] if p["name"] == "ztmm-declared-adapter"}
        assert names == {"a", "b"}

    def test_namespace_consistent(self):
        report = ZTMMScoreCalculator().score()
        resources = back_matter_resources_for_report(report)
        for r in resources:
            for p in r["props"]:
                assert p["ns"] == "https://uiao.gov/ns/oscal/ztmm"


# ---------------------------------------------------------------------------
# Substrate walker — pillar declaration scan
# ---------------------------------------------------------------------------


class TestSubstrateWalkerZTMMScan:
    def test_active_adapter_no_pillars_is_p3(self, tmp_path):
        canon = tmp_path / "src" / "uiao" / "canon"
        canon.mkdir(parents=True)
        (canon / "substrate-manifest.yaml").write_text(yaml.safe_dump({"modules": []}), encoding="utf-8")
        (canon / "modernization-registry.yaml").write_text(
            yaml.safe_dump({"adapters": [{"id": "skinny", "status": "active"}]}),
            encoding="utf-8",
        )

        from uiao.substrate.walker import walk_substrate

        report = walk_substrate(workspace_root=tmp_path)
        ztmm = [f for f in report.findings if "ztmm-pillars" in f.detail.lower()]
        assert len(ztmm) == 1
        assert ztmm[0].severity == "P3"

    def test_explicit_empty_pillars_clean(self, tmp_path):
        canon = tmp_path / "src" / "uiao" / "canon"
        canon.mkdir(parents=True)
        (canon / "substrate-manifest.yaml").write_text(yaml.safe_dump({"modules": []}), encoding="utf-8")
        (canon / "modernization-registry.yaml").write_text(
            yaml.safe_dump({"adapters": [{"id": "info", "status": "active", "ztmm-pillars": []}]}),
            encoding="utf-8",
        )
        from uiao.substrate.walker import walk_substrate

        report = walk_substrate(workspace_root=tmp_path)
        ztmm = [f for f in report.findings if "ztmm-pillars" in f.detail.lower()]
        assert ztmm == []

    def test_reserved_adapter_skipped(self, tmp_path):
        canon = tmp_path / "src" / "uiao" / "canon"
        canon.mkdir(parents=True)
        (canon / "substrate-manifest.yaml").write_text(yaml.safe_dump({"modules": []}), encoding="utf-8")
        (canon / "modernization-registry.yaml").write_text(
            yaml.safe_dump({"adapters": [{"id": "future", "status": "reserved"}]}),
            encoding="utf-8",
        )
        from uiao.substrate.walker import walk_substrate

        report = walk_substrate(workspace_root=tmp_path)
        ztmm = [f for f in report.findings if "ztmm-pillars" in f.detail.lower()]
        assert ztmm == []

    def test_real_canon_no_p3_ztmm_findings(self):
        """Live canon smoke: every active adapter declares ztmm-pillars,
        so the P3 advisory gate stays clean."""
        from uiao.substrate.walker import walk_substrate

        report = walk_substrate()
        p3 = [f for f in report.findings if "ztmm-pillars" in f.detail.lower()]
        assert p3 == [], f"Live canon has ZTMM-pillars findings: {p3}"


# ---------------------------------------------------------------------------
# End-to-end — live canon → calculator → report
# ---------------------------------------------------------------------------


def test_e2e_live_canon_yields_initial_or_better():
    """Pulling the live canon registries should yield at least INITIAL
    on every pillar — every pillar has at least one declared adapter."""
    decls = load_ztmm_declarations(
        [
            "src/uiao/canon/modernization-registry.yaml",
            "src/uiao/canon/adapter-registry.yaml",
        ]
    )
    calc = ZTMMScoreCalculator(declarations=decls)
    report = calc.score()
    for pillar in ZTMMPillar:
        score = report.scores[pillar]
        assert score.maturity != ZTMMMaturity.TRADITIONAL, f"{pillar.value} has zero declared adapters in live canon"
