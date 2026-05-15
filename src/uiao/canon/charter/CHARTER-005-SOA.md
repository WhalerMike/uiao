---
document_id: CHARTER-005-SOA
title: "UIAO Charter — Source of Authority: Location, Inter-Jurisdictional, Inter-Agency (cross-reference)"
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
  - "V4U source file Source_of_Authority_Location_InterAgency.md (Mar 7 2026 10:52) — concatenated into CHARTER-003 FILE 4 of 6"
  - "UIAO-V1 (Mar 9 2026): current authoritative charter — CHARTER-001"
provenance:
  source: "OneDrive: Application_Aware_Networking_White_Paper_by_Mike/V4/Backup/Source_of_Authority_Location_InterAgency.md (Mar 7 2026 10:52)"
  version: "1.0"
  derived_at: "2026-05-15"
  derived_by: "Charter Restoration Plan PR-A4"
  editorial_pass: "None — content not duplicated. The standalone source file is verbatim subsumed in CHARTER-003 (FILE 4 of 6). This document is a cross-reference, not a content duplicate."
canonical_location: "src/uiao/canon/charter/CHARTER-003.md (FILE 4 OF 6: Source of Authority — Location, Inter-Jurisdictional, Inter-Agency)"
ingestion_decision: "Charter Restoration Plan listed CHARTER-005-SOA as a separate ingestion in PR-A4. Verification at ingest time (2026-05-15) found the standalone source file (Source_of_Authority_Location_InterAgency.md, 171 lines, 18KB) to be 100% verbatim subsumed in CHARTER-003 FILE 4. To avoid duplicate canon (~18KB of identical content in two files), this CHARTER-005-SOA doc is a cross-reference to the canonical location in CHARTER-003. The CHARTER-005-SOA ID is preserved per the plan and provides per-topic addressability without content duplication."
---

# Source of Authority: Location, Inter-Jurisdictional, Inter-Agency

> **Cross-reference doc.** The canonical content for this charter
> entry is in [CHARTER-003 (V4U Master Reference)](CHARTER-003.md)
> under **FILE 4 of 6**:
>
> - **SOURCE OF AUTHORITY: LOCATION, INTER-JURISDICTIONAL, AND
>   INTER-AGENCY AUTHORITY CHAINS** — covers physical location and
>   building/facility authority (FRPP MS, GLC, FASTA), federal-to-state
>   authority relationships, and federal-to-federal authority
>   relationships.

## Why this is a cross-reference and not a duplicate

The standalone source file
`OneDrive:V4/Backup/Source_of_Authority_Location_InterAgency.md`
(Mar 7 2026 10:52, 171 lines, 18KB) was authored as a separate document.
At ~6 minutes later, the same content was concatenated verbatim into
`V4U_Master_Reference_All_Sections.md` (Mar 7 2026 10:58) as FILE 4 of
6. CHARTER-003 ingests the master reference; ingesting the standalone
file separately would land 18KB of duplicate canon.

A verification check at PR-A4 commit time (2026-05-15) confirmed the
standalone source content appears verbatim inside CHARTER-003:

```python
src = open("Source_of_Authority_Location_InterAgency.md").read()
charter003 = open("CHARTER-003.md").read()
assert src.strip() in charter003  # True
```

CHARTER-005-SOA is preserved as a cross-reference doc to (a) maintain
the ID allocation per the Charter Restoration Plan, (b) provide
per-topic addressability for downstream tools that look up
`CHARTER-005-SOA` directly, and (c) document the de-duplication
decision for future readers.

## When to read CHARTER-003 § FILE 4 directly

Read [CHARTER-003.md](CHARTER-003.md) §"FILE 4 OF 6: Source of
Authority — Location, Inter-Jurisdictional, Inter-Agency" when you
need:

- The Federal Real Property Profile Management System (FRPP MS) data
  model (location data elements: street address, lat/long, GLC, asset
  height, real property unique identifier, etc.).
- The Geographic Locator Code (GLC) reporting requirements.
- Federal-to-state authority chain patterns (E911, REAL ID, DMV/HR
  inter-jurisdictional flows).
- Federal-to-federal authority chain patterns (HRIT, OPM/USAccess
  inter-agency flows).

## Related charter entries

- **CHARTER-001** — UIAO-V1 main spec, §7 ("Source of Authority — The
  Chain of Authoritative Truth") references this content at the
  executive-summary level.
- **CHARTER-003** §FILE 3 — Source of Authority core (the broader SoA
  chain framework that this document extends with location and
  inter-agency dimensions).
- **CHARTER-003** §FILE 4 — full canonical content for this doc (this
  cross-reference points there).
- **CHARTER-004-NPE** — companion topic (also a cross-reference doc to
  CHARTER-003 §FILE 5).
