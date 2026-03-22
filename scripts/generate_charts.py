"""Generate dynamic data-driven charts from UIAO canon and compliance data.

Produces:
  - CISA ZT Maturity Radar chart (visuals/dynamic-maturity-radar.png)
  - Compliance Coverage bar chart (visuals/dynamic-compliance-coverage.png)

These are automatically embedded by generate_rich_docx.py and can be
referenced in Jinja templates via:
  ![Maturity Radar](../visuals/dynamic-maturity-radar.png)

Usage:
    python scripts/generate_charts.py
"""
import yaml
import logging
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for CI/CD
import matplotlib.pyplot as plt
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
CANON = ROOT / "canon" / "uiao_leadership_briefing_v1.0.yaml"
VISUALS_DIR = ROOT / "visuals"

MATURITY_SCORES = {
    "Traditional": 1,
    "Initial": 2,
    "Advanced": 3,
    "Optimal": 4,
}

UIAO_NAVY = "#1B3A5C"
UIAO_BLUE = "#4472C4"
UIAO_GREEN = "#2E7D32"
UIAO_GOLD = "#F9A825"


def load_context():
    """Load all data/*.yml and canon."""
    context = {}
    if DATA_DIR.exists():
        for yml_file in sorted(DATA_DIR.glob("*.yml")):
            key = yml_file.stem.replace("-", "_")
            with yml_file.open("r", encoding="utf-8") as f:
                content = yaml.safe_load(f)
            if content:
                if isinstance(content, dict):
                    context.update(content)
                context[key] = content
    if CANON.exists():
        with CANON.open("r", encoding="utf-8") as f:
            canon = yaml.safe_load(f)
        if canon:
            context.update(canon)
    return context


def generate_maturity_radar(context):
    """Generate a CISA Zero Trust Maturity radar chart."""
    mapping = context.get("cisa_zt_maturity_mapping", [])
    if not mapping:
        # Fallback: try unified_compliance_matrix
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

    N = len(labels)
    if N < 3:
        logger.warning("Need at least 3 data points for radar, got %d", N)
        return None

    angles = [n / float(N) * 2 * math.pi for n in range(N)]
    values_closed = values + values[:1]
    angles_closed = angles + angles[:1]

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw={"projection": "polar"})
    ax.set_theta_offset(math.pi / 2)
    ax.set_theta_direction(-1)

    ax.set_xticks(angles)
    ax.set_xticklabels(labels, fontsize=10, fontweight="bold", color=UIAO_NAVY)

    ax.set_ylim(0, 4.5)
    ax.set_yticks([1, 2, 3, 4])
    ax.set_yticklabels(["Traditional", "Initial", "Advanced", "Optimal"],
                       fontsize=7, color="#666")
    ax.yaxis.set_tick_params(labelsize=7)

    # Target line (Optimal)
    target = [4] * N + [4]
    ax.plot(angles_closed, target, "--", color=UIAO_GOLD, linewidth=1, alpha=0.5,
            label="Target: Optimal")
    ax.fill(angles_closed, target, alpha=0.05, color=UIAO_GOLD)

    # Current maturity
    ax.plot(angles_closed, values_closed, "o-", color=UIAO_BLUE, linewidth=2.5,
            markersize=8, label="Current Maturity")
    ax.fill(angles_closed, values_closed, alpha=0.25, color=UIAO_BLUE)

    ax.set_title("CISA Zero Trust Maturity Assessment\nUIAO Architecture",
                 fontsize=14, fontweight="bold", color=UIAO_NAVY, pad=20)
    ax.legend(loc="lower right", bbox_to_anchor=(1.15, -0.05), fontsize=9)

    out_path = VISUALS_DIR / "dynamic-maturity-radar.png"
    plt.tight_layout()
    plt.savefig(out_path, dpi=200, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    plt.close()
    logger.info("Maturity radar chart -> %s", out_path)
    return out_path


def generate_compliance_coverage(context):
    """Generate a compliance coverage bar chart."""
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

    bars1 = ax1.bar(x - width/2, control_counts, width, label="NIST Controls Mapped",
                    color=UIAO_BLUE, alpha=0.85)
    ax1.set_xlabel("UIAO Pillars", fontsize=11, fontweight="bold")
    ax1.set_ylabel("NIST 800-53 Controls", color=UIAO_BLUE, fontsize=11)
    ax1.set_xticks(x)
    ax1.set_xticklabels(pillars, rotation=30, ha="right", fontsize=9)
    ax1.tick_params(axis="y", labelcolor=UIAO_BLUE)

    ax2 = ax1.twinx()
    bars2 = ax2.bar(x + width/2, maturities, width, label="CISA Maturity Level",
                    color=UIAO_GREEN, alpha=0.7)
    ax2.set_ylabel("Maturity Level", color=UIAO_GREEN, fontsize=11)
    ax2.set_ylim(0, 5)
    ax2.set_yticks([1, 2, 3, 4])
    ax2.set_yticklabels(["Traditional", "Initial", "Advanced", "Optimal"], fontsize=8)
    ax2.tick_params(axis="y", labelcolor=UIAO_GREEN)

    # Value labels
    for bar in bars1:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                 f"{int(height)}", ha="center", va="bottom", fontsize=9, color=UIAO_BLUE)
    for bar in bars2:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height + 0.05,
                 ["?", "Trad", "Init", "Adv", "Opt"][int(height)],
                 ha="center", va="bottom", fontsize=8, color=UIAO_GREEN)

    ax1.set_title("UIAO Compliance Coverage & Maturity Assessment",
                  fontsize=14, fontweight="bold", color=UIAO_NAVY, pad=15)

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", fontsize=9)

    plt.tight_layout()
    out_path = VISUALS_DIR / "dynamic-compliance-coverage.png"
    plt.savefig(out_path, dpi=200, bbox_inches="tight",
                facecolor="white", edgecolor="none")
    plt.close()
    logger.info("Compliance coverage chart -> %s", out_path)
    return out_path


def main():
    logger.info("Loading UIAO context...")
    context = load_context()
    VISUALS_DIR.mkdir(parents=True, exist_ok=True)

    charts = []
    radar = generate_maturity_radar(context)
    if radar:
        charts.append(radar)
    coverage = generate_compliance_coverage(context)
    if coverage:
        charts.append(coverage)

    logger.info("Generated %d dynamic charts.", len(charts))
    if not charts:
        logger.warning("No charts generated. Check data files.")


if __name__ == "__main__":
    main()
