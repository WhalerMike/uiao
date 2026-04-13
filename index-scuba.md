# UIAO SCuBA Access Page

This page provides a canonical entry point for understanding how SCuBA (ScubaGear) assessments are executed, normalized, governed, and reported within the UIAO fabric.

---

## What is SCuBA?

SCuBA (Secure Cloud Business Applications) is a CISA-led effort to assess and harden cloud SaaS configurations such as Microsoft 365. The ScubaGear tool produces configuration assessment results that UIAO ingests and governs.

---

## What UIAO Adds

UIAO does not replace SCuBA; it **wraps** it in:

- Deterministic execution (adapter-run-scuba)
- Normalization into a canonical schema
- KSI-based evaluation and control mapping
- Provenance manifests for every run
- Clear separation of machine vs. human artifacts

---

## How to Run SCuBA via UIAO

1. Ensure required credentials and modules for ScubaGear are configured.
2. From the repository root, run:

```powershell
pwsh ./uiao-core/adapters/scuba/run/adapter-run-scuba.ps1 `
     -OutputDirectory ./uiao-core/artifacts/scuba
```

After completion, you will have:

- Raw SCuBA output (machine-facing)
- Normalized UIAO SCuBA document
- KSI-evaluated report
- Provenance manifest

---

## Where Artifacts Live

### Machine-facing (uiao-core)

- `uiao-core/artifacts/scuba/raw/`
- `uiao-core/artifacts/scuba/normalized/`
- `uiao-core/artifacts/scuba/reports/`
- `uiao-core/provenance/manifests/`

### Human-facing (uiao-docs)

- `uiao-docs/reports/SCuBA-Canonical-Report.md`
- `uiao-docs/appendices/Appendix-C-KSI-Mapping-Tables.md`
- `uiao-docs/appendices/Appendix-E-SCuBA-Field-Dictionary.md`

---

## Related Documents

- [UIAO SCuBA Integration and Governance Guide](./docs/SCuBA-Pipeline-Runbook.md)
- [Appendix B — UIAO SCuBA Pipeline](./appendices/Appendix-B-UIAO-SCuBA-Pipeline.md)
- [Appendix C — KSI Mapping Tables](./appendices/Appendix-C-KSI-Mapping-Tables.md)
- [Appendix E — SCuBA Field Dictionary](./appendices/Appendix-E-SCuBA-Field-Dictionary.md)

---

## Provenance

All artifacts produced by the UIAO SCuBA pipeline include a provenance manifest stored in:
`uiao-core/provenance/manifests/`

Manifests record: run metadata, file hashes, lineage, adapter version, and KSI ruleset version.

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
