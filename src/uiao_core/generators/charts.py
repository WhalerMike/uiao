"""Chart generator for UIAO compliance visualizations.

Migrated from scripts/generate_charts.py into the uiao_core package.
Produces CISA ZT Maturity Radar and Compliance Coverage bar charts
using matplotlib. Uses Agg backend for CI/CD compatibility.

NOTE: Only USA/territories visuals are generated (no world maps).
"""
from __future__ import annotations

import logging
import math
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

from uiao_core.utils.context import get_settings, load_context

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MATURITY_SCORES: dict[str, int] = {
    "Traditional": 1,
    "Initial": 2,
    "Advanced": 3,
    "Optimal": 4,
}

UIAO_NAVY = "#1B3A5C"
UIAO_BLUE = "#4472C4"
UIAO_GREEN = "#2E7D32"
UIAO_GOLD = "#F9A825"


# ---------------------------------------------------------------------------
# Chart builders
# ---------------------------------------------------------------------------
def generate_maturity_radar(
    context: dict[str, Any],
    output_dir: Path | None = None,
) -> Path | None:
    """Generate CISA Zero Trust Maturity radar chart."""
    if output_dir is None:
        output_dir = get_settings().project_root / "visuals"
    output_dir = Path(output_dir)

    mapping = context.get("cisa_zt_maturity_mapping", [])
    if not mapping:
        matrix = context.get("unified_compliance_matrix", [])
        if matrix:
            labels = [e.get("cisa_pillar", "?") for e in matrix]
            values = [MATURITY_SCORES.get(e.get("cisa_maturity", "Advanced"), 3) for e in matrix]
        else:
            logger.warning("No maturity data found, skipping radar chart.")
            return None
    else:
        labels = [e.get("pillar", "?") for e in mapping]
        values = [MATURITY_SCORES.get(e.get("maturity_level", "Advanced"), 3) for e in mapping]

    n = len(labels)
    if n < 3:
        logger.warning("Need at least 3 data points for radar, got %d", n)
        return None

    angles = [i / float(n) * 2 * math.pi for i in range(n)]
    values_closed = values + values[:1]
    angles_closed = angles + angles[:1]

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw={"projection": "polar"})
    ax.set_theta_offset(math.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_xticks(angles)
    ax.set_xticklabels(labels, fontsize=10, fontweight="bold", color=UIAO_NAVY)
    ax.set_ylim(0, 4.5)
    ax.set_yticks([1, 2, 3, 4])
    ax.set_yticklabels(
        ["Traditional", "Initial", "Advanced", "Optimal"],
        fontsize=7,
        color="#666",
    )

    target = [4] * n + [4]
    ax.plot(angles_closed, target, "--", color=UIAO_GOLD, linewidth=1, alpha=0.5, label="Target: Optimal")
    ax.fill(angles_closed, target, alpha=0.05, color=UIAO_GOLD)
    ax.plot(angles_closed, values_closed, "o-", color=UIAO_BLUE, linewidth=2.5, markersize=8, label="Current Maturity")
    ax.fill(angles_closed, values_closed, alpha=0.25, color=UIAO_BLUE)

    ax.set_title(
        "CISA Zero Trust Maturity Assessment\nUIAO Architecture",
        fontsize=14,
        fontweight="bold",
        color=UIAO_NAVY,
        pad=20,
    )
    ax.legend(loc="lower right", bbox_to_anchor=(1.15, -0.05), fontsize=9)

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "dynamic-maturity-radar.png"
    plt.tight_layout()
    plt.savefig(out_path, dpi=200, bbox_inches="tight", facecolor="white", edgecolor="none")
    plt.close()
    logger.info("Maturity radar chart -> %s", out_path)
    return out_path


def generate_compliance_coverage(
    context: dict[str, Any],
    output_dir: Path | None = None,
) -> Path | None:
    """Generate compliance coverage bar chart."""
    if output_dir is None:
        output_dir = get_settings().project_root / "visuals"
    output_dir = Path(output_dir)

    matrix = context.get("unified_compliance_matrix", [])
    if not matrix:
        logger.warning("No compliance matrix data, skipping coverage chart.")
        return None

    pillars = [e.get("pillar", "?") for e in matrix]
    control_counts = [len(e.get("nist_controls", [])) for e in matrix]
    maturities = [MATURITY_SCORES.get(e.get("cisa_maturity", "Advanced"), 3) for e in matrix]

    fig, ax1 = plt.subplots(figsize=(12, 6))
    x = np.arange(len(pillars))
    width = 0.35

    bars1 = ax1.bar(x - width/2, control_counts, width, label="NIST Controls Mapped", color=UIAO_BLUE, alpha=0.85)
    ax1.set_xlabel("UIAO Pillars", fontsize=11, fontweight="bold")
    ax1.set_ylabel("NIST 800-53 Controls", color=UIAO_BLUE, fontsize=11)
    ax1.set_xticks(x)
    ax1.set_xticklabels(pillars, rotation=30, ha="right", fontsize=9)
    ax1.tick_params(axis="y", labelcolor=UIAO_BLUE)

    ax2 = ax1.twinx()
    bars2 = ax2.bar(x + width/2, maturities, width, label="CISA Maturity Level", color=UIAO_GREEN, alpha=0.7)
    ax2.set_ylabel("Maturity Level", color=UIAO_GREEN, fontsize=11)
    ax2.set_ylim(0, 5)
    ax2.set_yticks([1, 2, 3, 4])
    ax2.set_yticklabels(["Traditional", "Initial", "Advanced", "Optimal"], fontsize=8)
    ax2.tick_params(axis="y", labelcolor=UIAO_GREEN)

    for bar in bars1:
        h = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., h + 0.1, f"{int(h)}", ha="center", va="bottom", fontsize=9, color=UIAO_BLUE)
    for bar in bars2:
        h = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., h + 0.05, ["?", "Trad", "Init", "Adv", "Opt"][int(h)], ha="center", va="bottom", fontsize=8, color=UIAO_GREEN)

    ax1.set_title("UIAO Compliance Coverage & Maturity Assessment", fontsize=14, fontweight="bold", color=UIAO_NAVY, pad=15)
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=9)

    plt.tight_layout()
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "dynamic-compliance-coverage.png"
    plt.savefig(out_path, dpi=200, bbox_inches="tight", facecolor="white", edgecolor="none")
    plt.close()
    logger.info("Compliance coverage chart -> %s", out_path)
    return out_path


def build_charts(
    canon_path: str | Path | None = None,
    data_dir: str | Path | None = None,
    output_dir: str | Path | None = None,
) -> list[Path]:
    """Build all charts. Returns list of generated file paths."""
    if output_dir is not None:
        output_dir = Path(output_dir)

    context = load_context(canon_path, data_dir)
    charts: list[Path] = []

    radar = generate_maturity_radar(context, output_dir)
    if radar:
        charts.append(radar)

    coverage = generate_compliance_coverage(context, output_dir)
    if coverage:
        charts.append(coverage)

    return charts
