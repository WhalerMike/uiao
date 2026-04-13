# UIAO SCuBA Maintainer Onboarding Guide

## 1. Purpose

This guide brings a new maintainer from zero context to fully capable of operating and evolving the UIAO SCuBA pipeline.

---

## 2. What You Are Responsible For

As a SCuBA maintainer, you:

- Run SCuBA assessments via the UIAO pipeline
- Ensure normalization and KSI evaluation succeed
- Maintain scripts, schemas, and mappings in **uiao-core**
- Maintain human-facing reports and docs in **uiao-docs**
- Preserve provenance and governance boundaries

---

## 3. Documents You Must Read First

1. **UIAO SCuBA Pipeline Runbook**
   [docs/SCuBA-Pipeline-Runbook.md](SCuBA-Pipeline-Runbook.md)

2. **Appendix B — UIAO SCuBA Pipeline (Summary & Diagrams)**
   [appendices/Appendix-B-UIAO-SCuBA-Pipeline.md](https://github.com/WhalerMike/uiao-docs/tree/main/appendices)

3. **KSI Ruleset and Mapping Tables**
   - KSI rules: `uiao-core/ksi/rules/`
   - Mapping tables: [Appendix C](https://github.com/WhalerMike/uiao-docs/tree/main/appendices)

---

## 4. One-Time Local Setup

- Install **PowerShell 7+**
- Install and configure **ScubaGear**
- Clone both repos:
  - `git clone https://github.com/WhalerMike/uiao-core.git`
  - `git clone https://github.com/WhalerMike/uiao-docs.git`
- Ensure you can run PowerShell scripts and commit/push to both repos

---

## 5. Running the Pipeline (Day-to-Day)

From the root of uiao-core:

```powershell
pwsh ./uiao-core/adapters/scuba/run/adapter-run-scuba.ps1 `
     -OutputDirectory ./uiao-core/artifacts/scuba
```

After a successful run, verify:

- Raw SCuBA output in `artifacts/scuba/raw/`
- Normalized JSON in `artifacts/scuba/normalized/`
- KSI report in `artifacts/scuba/reports/`
- Provenance manifest in `provenance/manifests/`

---

## 6. Updating the Human-Facing Report

1. Open the latest machine report: `uiao-core/artifacts/scuba/reports/ScubaResults.report.json`
2. Update the canonical human report: `uiao-docs/reports/SCuBA-Canonical-Report.md`
3. Commit with a clear message, e.g.:
   `chore(scuba): update canonical report for YYYY-MM-DD run`

---

## 7. Making Changes Safely

| Change | Action Required |
|---|---|
| Normalization logic | Update `normalize.ps1` and normalization schema |
| KSI rules | Update KSI ruleset YAML and evaluation script |
| Provenance schema | Update schema and generator script |
| Any non-trivial change | Add ADR entry, clear commit message, version bump |

---

## 8. When Things Break

| Problem | Capture and Report |
|---|---|
| SCuBA fails | Check credentials, ScubaGear install, execution policy |
| Normalization fails | Check raw JSON structure and schema drift |
| KSI evaluation fails | Check normalized JSON and KSI ruleset |
| Provenance fails | Check file paths and permissions |

If you cannot resolve: capture the command used, error output, and relevant file paths. Add to the Runbook troubleshooting section.

---

## 9. Your Mental Model

> "SCuBA is the sensor. UIAO is the fabric that normalizes, evaluates, and governs what SCuBA sees."

You are maintaining a governed pipeline with clear boundaries between:

- **Machine artifacts** (uiao-core)
- **Human artifacts** (uiao-docs)
- **Provenance and history** (both repos, no duplication)

---

## 10. Next Steps for a New Maintainer

1. Read the [Runbook](SCuBA-Pipeline-Runbook.md) end-to-end
2. Run the pipeline once in a non-production tenant
3. Walk through each artifact produced and map it to the Runbook
4. Review the KSI ruleset and mapping tables
5. Shadow a real production run (if applicable)

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
