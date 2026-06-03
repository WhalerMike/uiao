# uiao.adapters.zta — Zero Trust Assessment digest

Incorporates the output of Microsoft's open-source
[Zero Trust Assessment](https://github.com/microsoft/zerotrustassessment) into
UIAO as governed evidence — the ScubaGear pattern (UIAO_002 / UIAO_005) under
the ADR-092 Active Governance provider-incorporation contract.

UIAO **does not re-implement** the checks and **does not auto-remediate**. This
adapter consumes a report, recomputes roll-ups from `Tests[]` (the report's own
`TestResultSummary` is unreliable), derives a boundary-applicability signal from
existing fields, and renders human-facing digests.

## Usage

```powershell
# CLI (report is the .html the tool opens by default, or a .json export)
uiao zta digest --input .\ZeroTrustReport\ZeroTrustAssessmentReport.html --out-dir .\out

# pick formats / widen the worklist
uiao zta digest -i report.json -o .\out --format xlsx --format csv --risk High --risk Medium

# PowerShell wrapper (for analysts who don't invoke Python directly)
.\runtime\run\adapter-run-zta.ps1 -ReportPath .\ZeroTrustAssessmentReport.html
```

```python
from pathlib import Path
from uiao.adapters.zta import load_report, build_triage
from uiao.adapters.zta.render import write_outputs

triage = build_triage(load_report(Path("ZeroTrustAssessmentReport.html")))
write_outputs(triage, Path("./out"))            # exec, md, xlsx, html, csv
```

## Inputs

- `.html` — the report the tool opens by default. The full dataset is embedded
  as `reportData = {…}`; it is extracted with a JSON-aware decoder.
- `.json` — the structured export (identical schema).

## Outputs

| Format | File | Audience |
|---|---|---|
| `exec` | `<tenant>-<date>.exec.md` | one-page executive summary |
| `md` | `<tenant>-<date>.digest.md` | full triage digest |
| `xlsx` | `<tenant>-<date>.xlsx` | Summary / Worklist / All Tests / By Pillar |
| `html` | `<tenant>-<date>.digest.html` | slim self-contained companion |
| `csv` | `<tenant>-<date>.worklist.csv` | flat worklist for tooling |

## What the digest gets right

- **Recomputes from `Tests[]`** — never trusts `TestResultSummary` (it does not
  reconcile in shipped reports).
- **Six statuses, not pass/fail** — only `Failed` / `Investigate` are findings;
  `Skipped` / `Planned` / `Error` are surfaced as non-gaps.
- **Boundary applicability** derived from `SkippedReason` + `TestMinimumLicense`
  (premium/P2-SKU gating) — the GCC / FedRAMP Moderate "feature not in boundary
  vs control broken" distinction.
- **Dual `TestId` namespace** (numeric Graph checks + Azure GUIDs) tracked for
  the future 800-53/SCuBA crosswalk.

## Boundary / handling

Findings are tenant-specific vulnerability data → **Controlled**; keep output
in-boundary and do not publish raw results. Remediation is **proposed, not
applied** (federal L3 actuation ceiling). See the draft ADR in
`inbox/drafts/zero-trust-assessment-adapter/`.
