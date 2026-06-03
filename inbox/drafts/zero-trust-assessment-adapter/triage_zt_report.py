#!/usr/bin/env python3
"""
triage_zt_report.py — assess a Microsoft Zero Trust Assessment report.

Point it at any ZeroTrustAssessmentReport.json (the structured export that sits
alongside the .html the tool opens by default) and it prints an *honest* triage:

  * outcome distribution recomputed from Tests[]  (the TestResultSummary block is
    NOT trustworthy — in the shipped demo it does not reconcile with the per-test
    statuses, so we ignore it and recompute)
  * Pillar x Status crosstab
  * applicability signals (Skipped, Planned, premium/P2-SKU-gated) — the fields
    that matter under a GCC / FedRAMP Moderate boundary, where a low pass-rate is
    often "feature not in boundary", not "control broken"
  * the actionable core: High-risk + Failed worklist
  * dual TestId namespace report (short numeric Graph checks vs Azure GUIDs)

No third-party dependencies. Python 3.8+.

Usage:
    python triage_zt_report.py path\\to\\ZeroTrustAssessmentReport.json
    python triage_zt_report.py report.json --csv worklist.csv
    python triage_zt_report.py report.json --risk High Medium   # filter worklist
"""

from __future__ import annotations

import argparse
import contextlib
import csv
import json
import re
import sys
from collections import Counter, defaultdict

# Statuses the tool emits, in triage order. Only Failed/Investigate are findings
# that need action; Skipped/Planned/Error are applicability/coverage signals.
STATUSES = ["Failed", "Investigate", "Passed", "Skipped", "Planned", "Error"]
ACTIONABLE = {"Failed", "Investigate"}
RISK_ORDER = {"High": 0, "Medium": 1, "Low": 2, "": 3, None: 4}

# Substrings that indicate a premium / P2-class SKU. Presence is a proxy for
# "may not be available or authorized in a GCC-Moderate boundary" — verify per SKU.
PREMIUM_MARKERS = (
    "PREMIUM",
    "P2",
    "AAD_PREMIUM",
    "Entra_Premium",
    "Governance",
    "RMS_S_PREMIUM",
    "Azure_Firewall",
    "Azure_FrontDoor",
    "DDoS",
    "WAF",
)
_GUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-", re.ASCII)


def _utf8_stdout() -> None:
    """Windows consoles default to cp1252 and choke on the report's ✅/❌."""
    with contextlib.suppress(Exception):
        sys.stdout.reconfigure(encoding="utf-8")  # py3.7+


def license_str(test: dict) -> str:
    lic = test.get("TestMinimumLicense")
    if isinstance(lic, list):
        return ", ".join(str(x) for x in lic)
    return str(lic) if lic else ""


def is_premium(test: dict) -> bool:
    s = license_str(test)
    return any(m.lower() in s.lower() for m in PREMIUM_MARKERS)


def id_namespace(test_id: str) -> str:
    tid = str(test_id or "")
    if _GUID.match(tid):
        return "guid"  # Azure-resource checks
    if tid.isdigit():
        return "numeric"  # Graph-based checks
    return "other"


def load(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def section(title: str) -> None:
    print("\n" + title)
    print("-" * len(title))


def main() -> int:
    ap = argparse.ArgumentParser(description="Triage a Zero Trust Assessment JSON report.")
    ap.add_argument("report", help="path to ZeroTrustAssessmentReport.json")
    ap.add_argument("--csv", metavar="FILE", help="write the worklist to a CSV file")
    ap.add_argument(
        "--risk", nargs="+", default=["High"], help="risk levels to include in the worklist (default: High)"
    )
    ap.add_argument(
        "--status",
        nargs="+",
        default=sorted(ACTIONABLE),
        help="statuses to include in the worklist (default: Failed Investigate)",
    )
    args = ap.parse_args()

    _utf8_stdout()

    try:
        data = load(args.report)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: could not read {args.report}: {exc}", file=sys.stderr)
        return 2

    tests = data.get("Tests") or []
    if not tests:
        print("ERROR: no Tests[] array found — is this a Zero Trust Assessment report?", file=sys.stderr)
        return 2

    # ---- header --------------------------------------------------------------
    demo = " [DEMO DATA]" if data.get("IsDemo") else ""
    print(f"Zero Trust Assessment report{demo}")
    print(f"  Tenant : {data.get('TenantName')}  ({data.get('Domain')})")
    print(f"  Tool   : v{data.get('CurrentVersion')}   run {data.get('ExecutedAt')}")
    print(f"  Tests  : {len(tests)}")

    # ---- honest outcome distribution ----------------------------------------
    section("Outcome (recomputed from Tests[] — TestResultSummary is NOT trusted)")
    sc = Counter(t.get("TestStatus") for t in tests)
    for s in STATUSES:
        if sc.get(s):
            print(f"  {s:12}: {sc[s]}")
    other = {k: v for k, v in sc.items() if k not in STATUSES}
    for k, v in other.items():
        print(f"  {str(k):12}: {v}  (unrecognized status)")
    actionable = sum(sc.get(s, 0) for s in ACTIONABLE)
    print(
        f"  --> {actionable} actionable (Failed/Investigate); "
        f"{sc.get('Skipped', 0)} skipped, {sc.get('Planned', 0)} planned (tool roadmap, not gaps)"
    )

    # ---- pillar x status -----------------------------------------------------
    section("Pillar x Status")
    piv = defaultdict(Counter)
    for t in tests:
        piv[t.get("TestPillar") or "(none)"][t.get("TestStatus")] += 1
    print("  " + f"{'Pillar':<15}" + "".join(f"{s:<13}" for s in STATUSES))
    for p in sorted(piv):
        print("  " + f"{p:<15}" + "".join(f"{piv[p].get(s, 0):<13}" for s in STATUSES))

    # ---- applicability / boundary signals ------------------------------------
    section("Applicability signals (matter under GCC / FedRAMP Moderate)")
    prem = [t for t in tests if is_premium(t)]
    prem_failed = [t for t in prem if t.get("TestStatus") in ACTIONABLE]
    print(
        f"  premium/P2-SKU-gated tests : {len(prem)} of {len(tests)} "
        f"(verify each SKU's GCC availability before scoring as a gap)"
    )
    print(f"    ...of which actionable   : {len(prem_failed)}")
    skip_reasons = Counter(
        (t.get("SkippedReason") or "(no reason given)") for t in tests if t.get("TestStatus") == "Skipped"
    )
    if skip_reasons:
        print("  top skip reasons:")
        for reason, n in skip_reasons.most_common(5):
            print(f"    {n:>3}  {str(reason)[:80]}")

    # ---- dual ID namespace ---------------------------------------------------
    section("TestId namespaces (crosswalk key must handle both)")
    ns = Counter(id_namespace(t.get("TestId")) for t in tests)
    print(f"  numeric (Graph checks) : {ns.get('numeric', 0)}")
    print(f"  guid    (Azure checks) : {ns.get('guid', 0)}")
    if ns.get("other"):
        print(f"  other                  : {ns['other']}")

    # ---- actionable worklist -------------------------------------------------
    risk_set = set(args.risk)
    status_set = set(args.status)
    work = [t for t in tests if t.get("TestRisk") in risk_set and t.get("TestStatus") in status_set]
    work.sort(key=lambda t: (RISK_ORDER.get(t.get("TestRisk"), 9), t.get("TestPillar") or "", t.get("TestTitle") or ""))
    section(f"WORKLIST: risk={'/'.join(args.risk)} status={'/'.join(args.status)}  ({len(work)})")
    for t in work:
        flag = " [premium-SKU]" if is_premium(t) else ""
        print(
            f"  [{str(t.get('TestId')):>36}] {(t.get('TestPillar') or '-'):<14} {(t.get('TestTitle') or '')[:62]}{flag}"
        )

    # ---- optional CSV --------------------------------------------------------
    if args.csv:
        cols = [
            "TestId",
            "TestPillar",
            "TestCategory",
            "TestTitle",
            "TestRisk",
            "TestStatus",
            "TestImpact",
            "TestImplementationCost",
            "TestSfiPillar",
            "MinimumLicense",
            "PremiumGated",
            "IdNamespace",
        ]
        with open(args.csv, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            for t in work:
                w.writerow(
                    {
                        "TestId": t.get("TestId"),
                        "TestPillar": t.get("TestPillar"),
                        "TestCategory": t.get("TestCategory"),
                        "TestTitle": t.get("TestTitle"),
                        "TestRisk": t.get("TestRisk"),
                        "TestStatus": t.get("TestStatus"),
                        "TestImpact": t.get("TestImpact"),
                        "TestImplementationCost": t.get("TestImplementationCost"),
                        "TestSfiPillar": t.get("TestSfiPillar"),
                        "MinimumLicense": license_str(t),
                        "PremiumGated": is_premium(t),
                        "IdNamespace": id_namespace(t.get("TestId")),
                    }
                )
        print(f"\nWrote {len(work)} rows -> {args.csv}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
