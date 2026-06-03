"""ZT Assessment ↔ CISA SCuBA (ScubaGear) overlap classification.

Loads the surface-level crosswalk (``zta-scuba-overlap.yaml``) and classifies a
report's checks as **shared** with a ScubaGear baseline or **ZT-only**. This is a
surface map (which tool covers the area), not a 1:1 control mapping.
"""

from __future__ import annotations

import importlib.resources
from collections import Counter
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

import yaml

from uiao.adapters.zta.model import ZtReport, ZtTest

_MAPPING_FILE = "zta-scuba-overlap.yaml"


@lru_cache(maxsize=1)
def _mapping() -> dict[str, Any]:
    text = importlib.resources.files("uiao.adapters.zta").joinpath(_MAPPING_FILE).read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError(f"{_MAPPING_FILE} did not parse to a mapping")
    return data


@dataclass(frozen=True)
class Classification:
    """How one check relates to the SCuBA baselines."""

    scuba_product: str | None
    klass: str  # "shared" | "zt-only"
    surface: str

    @property
    def is_shared(self) -> bool:
        return self.klass == "shared"


def classify(pillar: str | None, category: str | None) -> Classification:
    """Classify a (pillar, category) onto the SCuBA surface or ZT-only."""
    m = _mapping()
    cat = (category or "").lower()
    for ov in m.get("category_overrides", []):
        scope = ov.get("pillar")
        if scope and scope != pillar:
            continue
        if str(ov.get("match", "")).lower() in cat:
            return Classification(ov.get("scuba"), ov.get("class", "zt-only"), ov.get("surface", ""))
    default = m.get("pillar_defaults", {}).get(pillar or "")
    if default is None:
        default = m.get("fallback", {"scuba": None, "class": "zt-only", "surface": "unclassified"})
    return Classification(default.get("scuba"), default.get("class", "zt-only"), default.get("surface", ""))


def classify_test(test: ZtTest) -> Classification:
    return classify(test.test_pillar, test.test_category)


@dataclass(frozen=True)
class OverlapMap:
    """Computed ZT↔SCuBA overlap for a report."""

    total: int
    shared: int
    zt_only: int
    by_pillar: dict[str, dict[str, int]]  # pillar -> {"shared": n, "zt-only": n}
    by_surface: dict[str, int]  # surface label -> count
    scuba_only: list[dict[str, str]] = field(default_factory=list)

    @property
    def shared_pct(self) -> int:
        return round(self.shared * 100 / self.total) if self.total else 0

    @property
    def zt_only_pct(self) -> int:
        return round(self.zt_only * 100 / self.total) if self.total else 0


def build_overlap(report: ZtReport) -> OverlapMap:
    """Classify every check and roll up the shared vs ZT-only split."""
    by_pillar: dict[str, dict[str, int]] = {}
    by_surface: Counter[str] = Counter()
    shared = 0
    for t in report.tests:
        c = classify_test(t)
        pillar = t.pillar
        row = by_pillar.setdefault(pillar, {"shared": 0, "zt-only": 0})
        row[c.klass] = row.get(c.klass, 0) + 1
        by_surface[c.surface or "(unclassified)"] += 1
        if c.is_shared:
            shared += 1
    total = len(report.tests)
    scuba_only = [dict(item) for item in _mapping().get("scuba_only", [])]
    return OverlapMap(
        total=total,
        shared=shared,
        zt_only=total - shared,
        by_pillar=dict(sorted(by_pillar.items())),
        by_surface=dict(by_surface.most_common()),
        scuba_only=scuba_only,
    )
