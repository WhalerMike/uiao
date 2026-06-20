#!/usr/bin/env python3
"""Compliance posture report — the compliance-side counterpart to the
governance corpus's reliability/heatmap instrumentation.

Governance ships ~89 self-monitoring docs (drift heatmaps, reliability scores,
early-warning models); compliance had no equivalent posture surface. This
report computes a point-in-time compliance posture from canonical in-repo data
across three panels:

  1. Control library — curated NIST 800-53 coverage and *narrative coverage*
     (how many of the curated controls carry an authored implementation
     narrative). Reuses ``scripts/check_control_library.py`` for the integrity
     numbers so the two never disagree.
  2. KSI library — the FedRAMP 20x Key Security Indicators (KSI-001…NNN),
     counted by severity. (Live pass/fail requires evaluation against tenant
     evidence; this is the static inventory.)
  3. POA&M — open Plan-of-Action-and-Milestones items and their aging.
     UIAO_189 ships as a template, so a reference deployment reports zero
     tracked items until instantiated.

Outputs a human-readable summary (default) or ``--json`` for dashboards/CI.
``--strict`` exits non-zero if the control library is internally inconsistent.

Usage:
  python scripts/compliance_posture_report.py
  python scripts/compliance_posture_report.py --json
  python scripts/compliance_posture_report.py --strict
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

import yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "scripts"
LIB_DIR = REPO_ROOT / "src" / "uiao" / "canon" / "data" / "control-library"
KSI_DIR = REPO_ROOT / "src" / "uiao" / "ksi" / "rules"
POAM_DOC = REPO_ROOT / "src" / "uiao" / "canon" / "UIAO_189_POAM_Template.md"

# Reuse the control-library integrity checker so the coverage numbers in this
# report and in CI come from one implementation.
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
from check_control_library import scan as scan_control_library  # noqa: E402


def control_panel() -> dict:
    """Curated control coverage + authored-narrative coverage."""
    integ = scan_control_library()
    with_narr = without_narr = 0
    missing: list[str] = []
    for fam in integ["families"]:
        for f in sorted((LIB_DIR / fam).glob("*.yml")):
            try:
                data = yaml.safe_load(f.read_text()) or {}
            except Exception:
                data = {}
            if str(data.get("narrative", "")).strip():
                with_narr += 1
            else:
                without_narr += 1
                missing.append(f.stem)
    total = integ["total_files"]
    return {
        "total_controls": total,
        "base": integ["base"],
        "enhancements": integ["enhancements"],
        "index_consistent": not integ["mismatches"],
        "narrative_coverage": {
            "with_narrative": with_narr,
            "without_narrative": without_narr,
            "pct": round(100 * with_narr / total, 1) if total else 0.0,
            "missing": sorted(missing),
        },
    }


def ksi_panel() -> dict:
    """FedRAMP 20x KSI inventory, by severity."""
    rules = sorted(KSI_DIR.glob("KSI-*.yaml"))
    by_sev: dict[str, int] = {}
    ids: list[str] = []
    for rf in rules:
        try:
            d = yaml.safe_load(rf.read_text()) or {}
        except Exception:
            d = {}
        ids.append(str(d.get("KSI_ID", rf.stem)))
        # Severity is a per-outcome map (e.g. {PASS: Low, FAIL: Critical});
        # the indicator's risk severity is its failure level.
        sev_raw = d.get("Severity", "Unspecified")
        if isinstance(sev_raw, dict):
            sev = str(sev_raw.get("FAIL") or sev_raw.get("WARN") or sev_raw.get("PASS") or "Unspecified")
        else:
            sev = str(sev_raw).strip() or "Unspecified"
        by_sev[sev] = by_sev.get(sev, 0) + 1
    return {
        "count": len(rules),
        "by_severity": dict(sorted(by_sev.items())),
        "ids": sorted(ids),
        "note": "Static inventory; live pass/fail requires evaluation against tenant evidence.",
    }


def poam_panel() -> dict:
    """Open POA&M items and aging. UIAO_189 is a template → zero until instantiated."""
    text = POAM_DOC.read_text() if POAM_DOC.exists() else ""
    # A real item carries a concrete POAM id (POAM-0001); the template only
    # shows the bracketed placeholder form [POAM-NNNN].
    import re

    real_ids = sorted(set(re.findall(r"\bPOAM-\d{4}\b", text)))
    return {
        "tracked_items": len(real_ids),
        "ids": real_ids,
        "is_template": len(real_ids) == 0,
        "note": "UIAO_189 ships as a template; a reference deployment tracks zero items until instantiated.",
    }


def build_report() -> dict:
    return {"control_library": control_panel(), "ksi": ksi_panel(), "poam": poam_panel()}


def _render_text(r: dict) -> str:
    c, k, p = r["control_library"], r["ksi"], r["poam"]
    nc = c["narrative_coverage"]
    lines = [
        "UIAO Compliance Posture Report",
        "=" * 44,
        "",
        "[1] Control library",
        f"    Curated controls : {c['total_controls']} (base {c['base']} + enhancements {c['enhancements']})",
        f"    index consistent : {'yes' if c['index_consistent'] else 'NO — run check_control_library.py'}",
        f"    Narrative coverage: {nc['with_narrative']}/{c['total_controls']} "
        f"({nc['pct']}%) — {nc['without_narrative']} without an authored narrative",
        "",
        "[2] KSI library (FedRAMP 20x)",
        f"    Indicators       : {k['count']}",
        f"    By severity      : {', '.join(f'{s}={n}' for s, n in k['by_severity'].items()) or '(none)'}",
        "",
        "[3] POA&M",
        f"    Tracked items    : {p['tracked_items']}"
        + ("  (template — none instantiated)" if p["is_template"] else ""),
    ]
    if nc["without_narrative"]:
        lines += ["", f"    Controls lacking a narrative: {', '.join(nc['missing'])}"]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    ap.add_argument(
        "--strict",
        action="store_true",
        help="exit 1 if the control library is internally inconsistent",
    )
    args = ap.parse_args()

    report = build_report()
    print(json.dumps(report, indent=2) if args.json else _render_text(report))

    if args.strict and not report["control_library"]["index_consistent"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
