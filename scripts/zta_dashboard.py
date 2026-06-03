#!/usr/bin/env python3
"""Analytics dashboard + Power BI dataset from a Zero Trust Assessment report.

Thin wrapper over ``uiao.adapters.zta`` — the implementation now lives in the
package (``uiao.adapters.zta.analytics`` + ``uiao.adapters.zta.render.dashboard``)
and is also exposed as ``uiao zta dashboard``. This script is kept for direct
invocation without the console entry point.

Usage::

    python scripts/zta_dashboard.py ZeroTrustAssessmentReport.html --out-dir ./zt-dashboard
    python scripts/zta_dashboard.py report.json -o ./out

Findings are tenant-specific Controlled data — keep output in-boundary and do
not publish raw results. Remediation is *proposed*, not applied (L3 ceiling).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from uiao.adapters.zta import load_report
from uiao.adapters.zta.analytics import build_facts, findings
from uiao.adapters.zta.render.dashboard import write_dashboard


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("report", type=Path, help="ZeroTrustAssessmentReport .html or .json")
    ap.add_argument("-o", "--out-dir", type=Path, default=Path("./zt-dashboard"), help="output directory")
    args = ap.parse_args()

    report = load_report(args.report)
    out = write_dashboard(report, args.out_dir)

    facts = build_facts(report)
    p1 = sum(1 for f in facts if f.bucket == "P1")
    print(f"Tenant: {report.tenant_name} ({len(report.tests)} checks, {len(findings(facts))} findings, {p1} P1)")
    print(f"Workbook : {out.workbook}")
    print(f"Power BI : {out.powerbi_csv}")
    print(f"Charts   : {out.charts[0].parent}")
    if report.is_demo:
        print("Note: this is Microsoft's DEMO report (IsDemo=true).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
