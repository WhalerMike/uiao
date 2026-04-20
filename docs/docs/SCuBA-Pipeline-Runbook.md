# UIAO SCuBA Pipeline Runbook

**Version:** 1.0
**Audience:** UIAO maintainers, modernization engineers, compliance operators
**Purpose:** Provide a complete, deterministic, end-to-end operational guide for executing, normalizing, evaluating, and governing SCuBA assessments inside the UIAO fabric.

---

## 1. Overview

The UIAO SCuBA Pipeline automates the execution of CISA's ScubaGear assessment tool and transforms its output into:

- A normalized, machine-readable UIAO schema
- A full KSI evaluation
- A provenance manifest
- A human-facing canonical report
- A drift-resistant artifact chain stored across uiao and uiao-docs

This runbook defines every step, every script, every output, and every governance boundary.

---

## 2. High-Level Pipeline Diagram

```
[1] Run SCuBA (adapter-run-scuba)
        ↓
[2] Raw SCuBA Output (JSON/CSV)
        ↓
[3] Normalization (normalize.ps1)
        ↓
[4] KSI Evaluation (evaluate-ksi.ps1)
        ↓
[5] Provenance Manifest (generate-manifest.ps1)
        ↓
[6] Machine Artifacts → uiao
        ↓
[7] Human Report → uiao-docs
```

---

## 3. Prerequisites

**Required:**

- PowerShell 7+
- ScubaGear installed and authenticated
- Access to the UIAO repository
- Permissions to write to uiao and uiao-docs

**Directory Structure:**

```
uiao/
  adapters/scuba/run/
  adapters/scuba/transforms/
  artifacts/scuba/{raw,normalized,reports}
  ksi/evaluations/
  provenance/manifests/

uiao-docs/
  reports/
  appendices/
  docs/
```

---

## 4. Running the Pipeline

The pipeline is executed through a single wrapper:

```powershell
pwsh ./uiao/adapters/scuba/run/adapter-run-scuba.ps1 `
     -OutputDirectory ./uiao/artifacts/scuba
```

This wrapper performs: SCuBA execution, normalization, KSI evaluation, and provenance generation.

---

## 5. Step-by-Step Execution

### Step 1 — Run SCuBA (ScubaGear)

Executed inside the wrapper. Output stored in:

```
uiao/artifacts/scuba/raw/
```

### Step 2 — Normalize SCuBA Output

**Script:** `uiao/adapters/scuba/transforms/normalize.ps1`

Converts raw ScubaGear JSON → UIAO normalized schema. Key responsibilities: extract metadata, map SCuBA fields to UIAO fields, enforce types, produce deterministic structure.

**Output:** `uiao/artifacts/scuba/normalized/ScubaResults.normalized.json`

### Step 3 — Evaluate KSI Rules

**Script:** `uiao/ksi/evaluations/evaluate-ksi.ps1`

Applies the full KSI ruleset (KSI-001 through KSI-010) to normalized SCuBA fields.

**Output:** `uiao/artifacts/scuba/reports/ScubaResults.report.json`

Contains: KSI IDs, PASS/WARN/FAIL status, severity, details.

### Step 4 — Generate Provenance Manifest

**Script:** `uiao/provenance/manifests/generate-manifest.ps1`

Hashes all artifacts, captures environment metadata, records lineage, produces immutable provenance.

**Output:** `uiao/provenance/manifests/prov-scuba-YYYYMMDD-HHMMSS.json`

---

## 6. Artifact Storage Model

### Machine-Facing (uiao)

| Directory | Contents |
|---|---|
| `artifacts/scuba/raw/` | Raw SCuBA JSON/CSV |
| `artifacts/scuba/normalized/` | Normalized UIAO schema |
| `artifacts/scuba/reports/` | KSI-evaluated machine report |
| `provenance/manifests/` | Provenance chain JSON |
| `adapters/scuba/` | Scripts, transforms, schemas |
| `ksi/` | Rules, evaluation engine |

### Human-Facing (uiao-docs)

| Directory | Contents |
|---|---|
| `reports/` | Canonical SCuBA human report |
| `appendices/` | Glossary, field dictionary, mappings |
| `docs/` | Runbooks, onboarding guides |
| `index-scuba.md` | Access page |

---

## 7. Human-Facing Canonical Report

Location: `uiao-docs/reports/SCuBA-Canonical-Report.md`

Contains: Executive summary, metadata, KSI summary, control mappings, detailed findings, provenance references.

---

## 8. Governance Boundaries

- Machine artifacts never stored in uiao-docs
- Human artifacts never stored in uiao
- No duplication across repos
- Every run produces a provenance manifest
- Every KSI rule is versioned
- Every adapter change requires an ADR

---

## 9. Troubleshooting

| Problem | Check |
|---|---|
| SCuBA fails to run | Credentials, ScubaGear install, PowerShell execution policy |
| Normalization fails | Raw SCuBA JSON structure, missing fields, schema drift |
| KSI evaluation fails | Normalized JSON validity, KSI ruleset version |
| Provenance fails | File paths, write permissions |

---

## 10. Quick Reference Commands

**Run entire pipeline:**
```powershell
pwsh ./uiao/adapters/scuba/run/adapter-run-scuba.ps1 `
     -OutputDirectory ./uiao/artifacts/scuba
```

**Normalize only:**
```powershell
pwsh ./uiao/adapters/scuba/transforms/normalize.ps1 `
     -InputPath raw.json `
     -OutputPath normalized.json
```

**Evaluate KSI only:**
```powershell
pwsh ./uiao/ksi/evaluations/evaluate-ksi.ps1 `
     -InputPath normalized.json `
     -OutputPath report.json
```

**Generate provenance only:**
```powershell
pwsh ./uiao/provenance/manifests/generate-manifest.ps1 `
     -RawFilePath raw.json `
     -NormalizedFilePath normalized.json `
     -ReportFilePath report.json `
     -OutputDirectory ./uiao/provenance/manifests
```

---

## 11. Related Documents

- [Appendix B — UIAO SCuBA Pipeline (Summary)](https://github.com/WhalerMike/uiao-docs/tree/main/appendices)
- [Appendix C — KSI Mapping Tables](https://github.com/WhalerMike/uiao-docs/tree/main/appendices)
- [SCuBA Canonical Report](https://github.com/WhalerMike/uiao-docs/tree/main/reports)
- [SCuBA Maintainer Onboarding Guide](SCuBA-Maintainer-Onboarding.md)
- [UIAO SCuBA Access Page](index.md)

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
