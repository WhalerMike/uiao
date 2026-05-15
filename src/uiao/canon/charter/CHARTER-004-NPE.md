---
document_id: CHARTER-004-NPE
title: "UIAO Charter — Federal Identity Fragmentation + NPE Assurance Model (cross-reference)"
version: "1.0"
status: Current
classification: CANONICAL
owner: Michael Stratton
boundary: GCC-Moderate
created_at: "2026-03-07"
updated_at: "2026-05-15"
tier: foundational
supersedable: false
load_order: 0
charter_chain:
  - "V4U source file Federal_Identity_Fragmentation_and_NPE_Assurance_Model.md (Mar 7 2026 10:51) — concatenated into CHARTER-003 FILE 5 of 6"
  - "UIAO-V1 (Mar 9 2026): current authoritative charter — CHARTER-001"
provenance:
  source: "OneDrive: Application_Aware_Networking_White_Paper_by_Mike/V4/Backup/Federal_Identity_Fragmentation_and_NPE_Assurance_Model.md (Mar 7 2026 10:51)"
  version: "1.0"
  derived_at: "2026-05-15"
  derived_by: "Charter Restoration Plan PR-A4"
  editorial_pass: "None — content not duplicated. The standalone source file is verbatim subsumed in CHARTER-003 (FILE 5 of 6, sections SECTION A + SECTION B). This document is a cross-reference, not a content duplicate."
canonical_location: "src/uiao/canon/charter/CHARTER-003.md (FILE 5 OF 6: Federal Identity Fragmentation + NPE Assurance Model)"
ingestion_decision: "Charter Restoration Plan listed CHARTER-004-NPE as a separate ingestion in PR-A4. Verification at ingest time (2026-05-15) found the standalone source file (Federal_Identity_Fragmentation_and_NPE_Assurance_Model.md, 251 lines, 25KB) to be 100% verbatim subsumed in CHARTER-003 FILE 5. To avoid duplicate canon (~25KB of identical content in two files), this CHARTER-004-NPE doc is a cross-reference to the canonical location in CHARTER-003. The CHARTER-004-NPE ID is preserved per the plan and provides per-topic addressability without content duplication."
---

# Federal Identity Fragmentation + NPE Assurance Model

> **Cross-reference doc.** The canonical content for this charter
> entry is in [CHARTER-003 (V4U Master Reference)](CHARTER-003.md)
> under **FILE 5 of 6**, comprising:
>
> - **SECTION A: FEDERAL IDENTITY FRAGMENTATION** — Five Disconnected
>   Regimes, One Architecture (REAL ID, PIV/CAC, NIST 800-63-4,
>   Login.gov/id.me, U.S. Passport — comparison table, fragmentation
>   problem, identity-forward reconciliation pattern)
> - **SECTION B: NON-PERSON ENTITY ASSURANCE MODEL** — Extending
>   Identity-Forward to Machines

## Why this is a cross-reference and not a duplicate

The standalone source file
`OneDrive:V4/Backup/Federal_Identity_Fragmentation_and_NPE_Assurance_Model.md`
(Mar 7 2026 10:51, 251 lines, 25KB) was authored as a separate document.
At ~7 minutes later, the same content was concatenated verbatim into
`V4U_Master_Reference_All_Sections.md` (Mar 7 2026 10:58) as FILE 5 of
6. CHARTER-003 ingests the master reference; ingesting the standalone
file separately would land 25KB of duplicate canon.

A verification check at PR-A4 commit time (2026-05-15) confirmed the
standalone source content appears verbatim inside CHARTER-003:

```python
src = open("Federal_Identity_Fragmentation_and_NPE_Assurance_Model.md").read()
charter003 = open("CHARTER-003.md").read()
assert src.strip() in charter003  # True
```

CHARTER-004-NPE is preserved as a cross-reference doc to (a) maintain
the ID allocation per the Charter Restoration Plan, (b) provide
per-topic addressability for downstream tools that look up
`CHARTER-004-NPE` directly, and (c) document the de-duplication
decision for future readers.

## When to read CHARTER-003 § FILE 5 directly

Read [CHARTER-003.md](CHARTER-003.md) §"FILE 5 OF 6: Federal Identity
Fragmentation + NPE Assurance Model" when you need:

- The five federal identity regimes comparison table (REAL ID, PIV/CAC,
  NIST 800-63-4, Login.gov/id.me, U.S. Passport).
- The fragmentation problem walkthrough (no cross-regime lifecycle,
  no shared identity graph, no technical interoperability).
- The Non-Person Entity (NPE) assurance model details.
- The identity-forward reconciliation architecture.

## Related charter entries

- **CHARTER-001** — UIAO-V1 main spec, §4 ("Federal Identity
  Fragmentation") references this content at the executive-summary
  level.
- **CHARTER-003** §FILE 5 — full canonical content (this doc points to it).
- **CHARTER-005-SOA** — companion SoA topic (also a cross-reference doc
  to CHARTER-003 §FILE 4).
