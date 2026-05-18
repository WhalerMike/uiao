"""ZTMM Integration — adapter→pillar mapping + maturity scoring (UIAO_120, §3.6).

This module ships the substrate's CISA Zero Trust Maturity Model (ZTMM)
v2.0 alignment surface. Each active adapter declares the ZTMM pillars
its evidence outputs inform via a ``ztmm-pillars:`` field in canon.
A scorer aggregates declarations + evidence-graph coverage into a
per-pillar maturity score (Traditional / Initial / Advanced / Optimal).

CISA ZTMM v2.0 reference: https://www.cisa.gov/zero-trust-maturity-model

Pillars (5):
    IDENTITY                     User / service / device-identity governance
    DEVICES                      Endpoint posture, MDM coverage
    NETWORKS                     Microsegmentation, encrypted transit
    APPLICATIONS_AND_WORKLOADS   App-layer policy, runtime protection
    DATA                         Classification, encryption-at-rest, DLP

Maturity (4 levels, low → high):
    TRADITIONAL    No automation; manual config, ad-hoc evidence
    INITIAL        ≥1 adapter declared on the pillar
    ADVANCED       ≥2 adapters declared AND ≥1 has evidence in the graph
    OPTIMAL        ≥3 adapters declared AND all declared have fresh evidence

Pipeline:

    canon registries (modernization-registry + adapter-registry)
            │
            ▼
    load_ztmm_declarations(registries) → {adapter_id: AdapterZTMMDeclaration}
            │
            ├──── EvidenceGraph (UIAO_113) ────────┐
            ▼                                       │
    ZTMMScoreCalculator.score(graph) ──────────────┘
            │
            ▼
    ZTMMReport {pillar: ZTMMPillarScore}
            │
            ▼
    OSCAL back-matter resources (one per pillar, deterministic UUID)

The integration mirrors the §0.4 (consent envelope) and §0.5
(issuer-chain) governance modules: registry-driven declarations,
scoring projection, OSCAL surfacing.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

import yaml

from uiao.evidence.graph import EvidenceGraph

# ---------------------------------------------------------------------------
# Vocabulary — CISA ZTMM v2.0
# ---------------------------------------------------------------------------


class ZTMMPillar(str, Enum):
    """CISA ZTMM v2.0 pillars."""

    IDENTITY = "identity"
    DEVICES = "devices"
    NETWORKS = "networks"
    APPLICATIONS_AND_WORKLOADS = "applications-and-workloads"
    DATA = "data"

    @classmethod
    def parse(cls, value: str) -> Optional[ZTMMPillar]:
        """Best-effort parse from a canon ``ztmm-pillars:`` entry.

        Accepts the canonical kebab-case form, common abbreviations
        ("apps" / "workloads" → APPLICATIONS_AND_WORKLOADS), and
        plural/singular variants.
        """
        if not value:
            return None
        norm = str(value).strip().lower().replace("_", "-").replace(" ", "-")
        synonyms = {
            "identity": cls.IDENTITY,
            "identities": cls.IDENTITY,
            "device": cls.DEVICES,
            "devices": cls.DEVICES,
            "endpoint": cls.DEVICES,
            "endpoints": cls.DEVICES,
            "network": cls.NETWORKS,
            "networks": cls.NETWORKS,
            "application": cls.APPLICATIONS_AND_WORKLOADS,
            "applications": cls.APPLICATIONS_AND_WORKLOADS,
            "applications-and-workloads": cls.APPLICATIONS_AND_WORKLOADS,
            "apps": cls.APPLICATIONS_AND_WORKLOADS,
            "app": cls.APPLICATIONS_AND_WORKLOADS,
            "workload": cls.APPLICATIONS_AND_WORKLOADS,
            "workloads": cls.APPLICATIONS_AND_WORKLOADS,
            "data": cls.DATA,
        }
        return synonyms.get(norm)


class ZTMMMaturity(str, Enum):
    """CISA ZTMM v2.0 maturity stages."""

    TRADITIONAL = "traditional"
    INITIAL = "initial"
    ADVANCED = "advanced"
    OPTIMAL = "optimal"

    @property
    def rank(self) -> int:
        """Numeric rank for ordering / comparison (0 = lowest)."""
        return {
            ZTMMMaturity.TRADITIONAL: 0,
            ZTMMMaturity.INITIAL: 1,
            ZTMMMaturity.ADVANCED: 2,
            ZTMMMaturity.OPTIMAL: 3,
        }[self]


# Stable namespace UUID for deriving deterministic resource UUIDs from a
# pillar id. Sibling to _OSCAL_GRAPH_RESOURCE_NS in evidence/graph.py.
_OSCAL_ZTMM_RESOURCE_NS = uuid.UUID("c0f4d2a1-2b8e-5f93-9c47-7a1e4c6d8120")


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AdapterZTMMDeclaration:
    """One adapter's declared contribution to ZTMM pillars."""

    adapter_id: str
    pillars: frozenset[ZTMMPillar] = frozenset()

    @property
    def declared(self) -> bool:
        return bool(self.pillars)


@dataclass(frozen=True)
class ZTMMPillarScore:
    """Per-pillar maturity rollup."""

    pillar: ZTMMPillar
    maturity: ZTMMMaturity
    declared_adapters: tuple[str, ...]
    """Adapters that declared this pillar."""
    evidenced_adapters: tuple[str, ...]
    """Subset of declared_adapters that have at least one EvidenceNode in
    the graph (any control)."""
    fresh_adapters: tuple[str, ...]
    """Subset of evidenced_adapters whose evidence carries no Open
    finding for any of their evidenced controls — proxy for fresh
    coverage."""

    def as_dict(self) -> dict[str, Any]:
        return {
            "pillar": self.pillar.value,
            "maturity": self.maturity.value,
            "rank": self.maturity.rank,
            "declared_adapters": list(self.declared_adapters),
            "evidenced_adapters": list(self.evidenced_adapters),
            "fresh_adapters": list(self.fresh_adapters),
        }


@dataclass(frozen=True)
class ZTMMReport:
    """Whole-substrate ZTMM rollup."""

    scores: Mapping[ZTMMPillar, ZTMMPillarScore]

    @property
    def overall_rank(self) -> float:
        """Average maturity rank across all five pillars."""
        if not self.scores:
            return 0.0
        return sum(s.maturity.rank for s in self.scores.values()) / len(self.scores)

    def as_dict(self) -> dict[str, Any]:
        return {
            "scores": {p.value: s.as_dict() for p, s in self.scores.items()},
            "overall_rank": self.overall_rank,
        }


# ---------------------------------------------------------------------------
# Registry loader
# ---------------------------------------------------------------------------


def _adapter_entries(doc: Optional[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    if not doc:
        return []
    if isinstance(doc, list):
        return [a for a in doc if isinstance(a, Mapping)]
    candidates = doc.get("adapters") or doc.get("modernization_adapters")
    if isinstance(candidates, list):
        return [a for a in candidates if isinstance(a, Mapping)]
    return []


def load_ztmm_declarations(
    registries: Iterable[str | Path],
) -> dict[str, AdapterZTMMDeclaration]:
    """Read registry YAMLs and return ``{adapter_id: AdapterZTMMDeclaration}``.

    Adapters without a ``ztmm-pillars:`` key are absent from the result —
    distinct from an explicit empty list, which yields a declaration with
    no pillars. Later registries override earlier.
    """
    out: dict[str, AdapterZTMMDeclaration] = {}
    for path in registries:
        p = Path(path)
        if not p.is_file():
            continue
        try:
            doc = yaml.safe_load(p.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            continue
        for entry in _adapter_entries(doc):
            adapter_id = str(entry.get("id", "")).strip()
            if not adapter_id:
                continue
            if "ztmm-pillars" not in entry:
                continue
            raw = entry.get("ztmm-pillars") or []
            pillars: set[ZTMMPillar] = set()
            if isinstance(raw, list):
                for token in raw:
                    parsed = ZTMMPillar.parse(str(token))
                    if parsed is not None:
                        pillars.add(parsed)
            out[adapter_id] = AdapterZTMMDeclaration(adapter_id=adapter_id, pillars=frozenset(pillars))
    return out


# ---------------------------------------------------------------------------
# Score calculator
# ---------------------------------------------------------------------------


@dataclass
class ZTMMScoreCalculator:
    """Compute per-pillar ZTMM maturity from declarations + graph state.

    Maturity rubric (low → high):
        TRADITIONAL    no adapter declared on the pillar
        INITIAL        ≥1 adapter declared
        ADVANCED       ≥2 adapters declared AND ≥1 has evidence
        OPTIMAL        ≥3 adapters declared AND all declared have evidence
                       AND none has an Open finding

    The thresholds are deliberately conservative — Phase 0 substrates
    typically land at INITIAL across the board even with full canon
    coverage; ADVANCED requires real adapter dispatch into the graph;
    OPTIMAL requires steady-state freshness.
    """

    declarations: Mapping[str, AdapterZTMMDeclaration] = field(default_factory=dict)

    def _adapters_for_pillar(self, pillar: ZTMMPillar) -> list[str]:
        return sorted(d.adapter_id for d in self.declarations.values() if pillar in d.pillars)

    def _evidence_count(self, graph: Optional[EvidenceGraph], adapter_id: str) -> int:
        """Count EvidenceNodes whose source matches the adapter id."""
        if graph is None:
            return 0
        count = 0
        for node in graph.nodes_of_type("evidence"):
            if getattr(node, "source", "") == adapter_id:
                count += 1
        return count

    def _has_open_finding(self, graph: Optional[EvidenceGraph], adapter_id: str) -> bool:
        """True when any FindingNode in the graph names this adapter via
        its ``extra.adapter_id`` (set during scheduler-run ingestion).
        """
        if graph is None:
            return False
        for node in graph.nodes_of_type("finding"):
            extra = getattr(node, "extra", {}) or {}
            if extra.get("adapter_id") == adapter_id and getattr(node, "status", "") == "Open":
                return True
        return False

    def score_pillar(
        self,
        pillar: ZTMMPillar,
        graph: Optional[EvidenceGraph] = None,
    ) -> ZTMMPillarScore:
        declared = self._adapters_for_pillar(pillar)
        evidenced: list[str] = []
        fresh: list[str] = []
        for aid in declared:
            ev_count = self._evidence_count(graph, aid)
            if ev_count > 0:
                evidenced.append(aid)
                if not self._has_open_finding(graph, aid):
                    fresh.append(aid)

        if not declared:
            maturity = ZTMMMaturity.TRADITIONAL
        elif len(declared) >= 3 and evidenced and len(fresh) == len(declared):
            maturity = ZTMMMaturity.OPTIMAL
        elif len(declared) >= 2 and evidenced:
            maturity = ZTMMMaturity.ADVANCED
        else:
            maturity = ZTMMMaturity.INITIAL

        return ZTMMPillarScore(
            pillar=pillar,
            maturity=maturity,
            declared_adapters=tuple(declared),
            evidenced_adapters=tuple(evidenced),
            fresh_adapters=tuple(fresh),
        )

    def score(self, graph: Optional[EvidenceGraph] = None) -> ZTMMReport:
        scores = {pillar: self.score_pillar(pillar, graph=graph) for pillar in ZTMMPillar}
        return ZTMMReport(scores=scores)


# ---------------------------------------------------------------------------
# OSCAL back-matter resource projection
# ---------------------------------------------------------------------------


def _resource_uuid_for_pillar(pillar: ZTMMPillar) -> str:
    """Deterministic UUID for an OSCAL back-matter resource keyed on the
    pillar id. Same pillar → same UUID across all OSCAL artifacts."""
    return str(uuid.uuid5(_OSCAL_ZTMM_RESOURCE_NS, pillar.value))


def back_matter_resources_for_report(
    report: ZTMMReport,
) -> list[dict[str, Any]]:
    """Build OSCAL back-matter resources surfacing the ZTMM report.

    One resource per pillar (5 resources total). Each carries
    ``maturity``, ``rank``, declared/evidenced/fresh adapter lists as
    OSCAL props under the ``https://uiao.gov/ns/oscal/ztmm`` namespace.
    """
    ns = "https://uiao.gov/ns/oscal/ztmm"
    out: list[dict[str, Any]] = []
    for pillar in ZTMMPillar:
        score = report.scores.get(pillar)
        if score is None:
            continue
        props = [
            {"name": "ztmm-pillar", "value": pillar.value, "ns": ns},
            {"name": "ztmm-maturity", "value": score.maturity.value, "ns": ns},
            {"name": "ztmm-rank", "value": str(score.maturity.rank), "ns": ns},
            {
                "name": "ztmm-declared-count",
                "value": str(len(score.declared_adapters)),
                "ns": ns,
            },
            {
                "name": "ztmm-evidenced-count",
                "value": str(len(score.evidenced_adapters)),
                "ns": ns,
            },
            {
                "name": "ztmm-fresh-count",
                "value": str(len(score.fresh_adapters)),
                "ns": ns,
            },
        ]
        for aid in score.declared_adapters:
            props.append({"name": "ztmm-declared-adapter", "value": aid, "ns": ns})
        out.append(
            {
                "uuid": _resource_uuid_for_pillar(pillar),
                "title": f"UIAO ZTMM pillar score: {pillar.value}",
                "description": (
                    f"CISA Zero Trust Maturity Model v2.0 — {pillar.value} pillar "
                    f"score: {score.maturity.value} (rank {score.maturity.rank}). "
                    f"Declared by {len(score.declared_adapters)} adapter(s); "
                    f"{len(score.evidenced_adapters)} have evidence in graph; "
                    f"{len(score.fresh_adapters)} are fresh."
                ),
                "props": props,
            }
        )
    return out


__all__ = [
    "AdapterZTMMDeclaration",
    "ZTMMMaturity",
    "ZTMMPillar",
    "ZTMMPillarScore",
    "ZTMMReport",
    "ZTMMScoreCalculator",
    "back_matter_resources_for_report",
    "load_ztmm_declarations",
]
