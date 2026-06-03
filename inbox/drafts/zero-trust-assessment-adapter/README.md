# Zero Trust Assessment incorporation — working draft

Staging area for incorporating Microsoft's open-source **Zero Trust Assessment**
(`github.com/microsoft/zerotrustassessment`) output into UIAO as governed
evidence. Pattern is the ScubaGear one already in canon (UIAO_002 / UIAO_005),
under the ADR-092 (Active Governance) provider-incorporation contract.

## Contents

| File | What it is |
|---|---|
| `adr-zero-trust-assessment-incorporation.DRAFT.md` | Draft ADR + the JSON→canonical-evidence **mapping spec**. ADR number is a placeholder — assign at promotion (ADR-092 is in flight, PR #755). |
| `triage_zt_report.py` | Reusable triage tool — run against any `…Report.json`. No dependencies, Python 3.8+. |
| `SampleReport.json` | Microsoft's shipped demo report (Contoso, tool v2.1.8, 295 tests). Reference fixture — safe, no real tenant data (`IsDemo: true`). |

## Using the triage tool

```powershell
# default: High-risk Failed/Investigate worklist + honest roll-ups
python triage_zt_report.py SampleReport.json

# widen the worklist and export to CSV
python triage_zt_report.py SampleReport.json --risk High Medium --csv worklist.csv
```

It deliberately **ignores `TestResultSummary`** (unreliable — see the ADR) and
recomputes everything from `Tests[]`. It flags premium/P2-SKU-gated checks
(GCC-Moderate availability risk) and reports the dual `TestId` namespace.

## At work

Your tool output is the `.html`; the same data is in the JSON the run produces.
Check the `\zt-export\` folder (or re-run with `-Path`) for a `…Report.json`,
then point `triage_zt_report.py` at it. **The JSON is Controlled tenant data** —
keep it in-boundary; do not commit a real export to the repo.

## Next steps (see ADR open questions)

1. Confirm a real export matches the `SampleReport.json` schema.
2. Decide where the `TestId` → 800-53-Moderate / SCuBA crosswalk table lives.
3. Pick the customer-facing surface (Book chapter vs ADR-092 Platform page).
