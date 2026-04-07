# Appendix B — UIAO SCuBA Pipeline

## B.1 Purpose

This appendix provides a concise overview of the UIAO SCuBA Pipeline, including its major stages, artifacts, and governance boundaries. It is a summary reference; the full operational details are documented in the **UIAO SCuBA Pipeline Runbook** at `docs/SCuBA-Pipeline-Runbook.md`.

---

## B.2 High-Level Pipeline Summary

The UIAO SCuBA Pipeline automates the execution of CISA's ScubaGear assessment and transforms its output into:

- A normalized UIAO schema
- A KSI-evaluated machine report
- A provenance manifest
- A human-facing canonical report

Core stages:

1. **Run SCuBA** via adapter-run-scuba
2. **Normalize** raw SCuBA output into the UIAO schema
3. **Evaluate KSI** rules against normalized fields
4. **Generate provenance** for all artifacts
5. **Publish human report** in uiao-docs

---

## B.3 Diagram 1 — SCuBA With vs. Without UIAO

```
Without UIAO
------------
[ScubaGear] → [Raw Output (JSON/CSV)]
              (Ad hoc storage, no normalization,
               no KSI, no provenance)

With UIAO
---------
[ScubaGear] → [Raw Output] → [UIAO Normalization] → [KSI Evaluation]
                                   |                      |
                              (uiao-core)             (uiao-core)
                                                          ↓
                                                    [Provenance]
                                                          ↓
                                                  [Human Report]
                                                   (uiao-docs)
```

---

## B.4 Diagram 2 — UIAO SCuBA Pipeline

```
[1] adapter-run-scuba.ps1
        ↓
[2] Raw SCuBA Output
    (uiao-core/artifacts/scuba/raw)
        ↓
[3] normalize.ps1
    (uiao-core/adapters/scuba/transforms)
        ↓
[4] Normalized SCuBA JSON
    (uiao-core/artifacts/scuba/normalized)
        ↓
[5] evaluate-ksi.ps1
    (uiao-core/ksi/evaluations)
        ↓
[6] KSI Report JSON
    (uiao-core/artifacts/scuba/reports)
        ↓
[7] generate-manifest.ps1
    (uiao-core/provenance/manifests)
        ↓
[8] Human-Facing Report
    (uiao-docs/reports/SCuBA-Canonical-Report.md)
```

---

## B.5 Diagram 3 — SCuBA → KSI → Control Mapping

```
[SCuBA Fields]
    MFAEnabled
    LegacyAuthEnabled
    AdminCount
    ...
        ↓
[UIAO Normalized Fields]
    normalized.fields.MFAEnabled
    normalized.fields.LegacyAuthEnabled
    ...
        ↓
[KSI Rules]
    KSI-001 (MFA)
    KSI-002 (Legacy Auth)
    ...
        ↓
[Controls]
    NIST 800-53
    FedRAMP
    CISA SCuBA IDs
```

---

## B.6 Governance Boundaries (Summary)

- Machine artifacts: **uiao-core only**
- Human artifacts: **uiao-docs only**
- No duplication across repos
- Every SCuBA run produces a provenance manifest
- Every KSI rule is versioned
- Every adapter change requires an ADR

Full operational details: [UIAO SCuBA Pipeline Runbook](../docs/SCuBA-Pipeline-Runbook.md)
