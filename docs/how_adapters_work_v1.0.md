---
title: "How Adapters Work V1.0"
author: "UIAO Modernization Program"
date: today
date-format: "MMMM D, YYYY"
format:
  html: default
  docx: default
  pdf: default
  gfm: default
---

# How Adapters Work — UIAO DNS-Style Resolution Pattern

**Version:** 1.0  
**Status:** Authoritative  
**Repository:** `uiao-core`  
**Classification:** CUI/FOUO  
**Last Updated:** April 2026

---

## Overview

The UIAO adapter framework is intentionally **lightweight and sits outside the main data path**. Its only job is to **create alignments** — vendor-overlay references, identity-rooted claims, and evidence hashes — that the downstream generation engine consumes.

Adapters do **not** perform the actual conversions into OSCAL JSON, SSPs, POA&Ms, or SBOMs. Those happen in the `generators/` layer. The adapters simply tell the engine how to get there.

This design follows the same principle as DNS: a resolver does not host your website — it tells your browser where to find it.

---

## The DNS Analogy

The adapter pattern maps directly to how DNS resolution works:

| DNS Concept | UIAO Adapter Equivalent | What It Does |
|---|---|---|
| Domain name | YAML canon (Single Source of Truth) | The one authoritative address |
| DNS resolver | Adapter (Entra, ServiceNow, Palo Alto, etc.) | "Tells you how to get there" |
| IP address returned | Vendor-overlay + claim alignment | Pointer + mapping + evidence hash |
| Recursive lookup | Collector → normalize → overlay | Fast, repeatable, no data duplication |
| TTL / cache invalidation | Drift detection | Continuous validation against canon |
| No data storage | Adapters never own or duplicate data | Keeps SSOT pure |

The adapter's only job is to say:  
> "Hey engine — here's the authoritative vendor record for this identity/control, here's how it maps to our UIAO schema, and here's the evidence hash."

Then the **generators/** layer (the real workhorse) does the heavy lifting: turning the aligned claims into full OSCAL JSON, SSPs, POA&Ms, SBOMs, drift reports, and compliance artifacts.

---

## Adapter Resolution Flow

```
                        UIAO Adapter Pattern (DNS-Style Resolution)

  ┌─────────────────┐      ┌─────────────────────┐      ┌──────────────────┐
  │  YAML Canon      │      │  Adapter (Resolver)  │      │  Vendor System   │
  │  (SSOT)          │      │                      │      │  (Entra, SNOW,   │
  │                  │      │  1. Connect           │<─────│   Palo Alto...)  │
  │  "The domain     │      │  2. Collect (API)     │      │                  │
  │   name"          │      │  3. Normalize         │      │  Raw records,    │
  │                  │      │  4. Align → overlay   │      │  events, configs │
  └────────┬─────────┘      └──────────┬────────────┘      └──────────────────┘
           │                           │
           │   Vendor-overlay +        │
           │   claim alignment         │
           │   ("IP address")          │
           ▼                           ▼
  ┌──────────────────────────────────────────────────────────────────────┐
  │                     Generation Engine (generators/)                  │
  │                                                                      │
  │   Aligned claims ──> OSCAL JSON, SSP, POA&M, SBOM, DOCX, PPTX      │
  │                                                                      │
  │   The engine does the heavy lifting. Adapters just point the way.   │
  └──────────────────────────────────────────────────────────────────────┘
```

---

## What an Adapter Actually Does (Step-by-Step)

Every adapter in the Big 7 framework follows the same four-step resolution pattern:

### Step 1 — Connect

The **collector** establishes a secure connection to the vendor system using OAuth client credentials, API keys, or mTLS. It returns a `ConnectionProvenance` record capturing the identity, auth method, endpoint, and TLS version.

```
Collector → Vendor API (Graph, ServiceNow REST, Panorama, etc.)
         ← ConnectionProvenance (identity, endpoint, tls, timestamp)
```

### Step 2 — Collect

The collector queries the vendor API for raw records relevant to the target KSI or control family. It does not filter or transform — it returns the raw payload.

```
Collector.collect(ksi_id="AC-2")
         ← EvidencePackage (raw_data, source, timestamp, hash)
```

### Step 3 — Normalize

The **adapter** transforms raw vendor records into canonical UIAO `ClaimObject` entries. Each claim binds:

- **Identity** — the root namespace (`entra:user:abc123`, `snow:incident:INC0012345`)
- **Control ID** — the NIST control this claim maps to
- **Implementation statement** — what the vendor record proves
- **Vendor-overlay reference** — pointer to `data/vendor-overlays/<vendor>.yaml`
- **Evidence hash** — SHA-256 of the raw record for provenance

```python
ClaimObject(
    claim_id   = "entra:abc123",
    entity     = "entra:user:abc123",
    fields     = { identity, control_id, implementation_statement, ... },
    source     = "entra",
    provenance_hash = sha256(raw_record)
)
```

### Step 4 — Align to Overlay

The adapter packages all claims into a `ClaimSet` with a source reference back to the vendor API. The engine merges this alignment into the canon and hands it to the generators for full artifact creation.

```
Adapter.normalize(raw_rows)
       ← ClaimSet (claims[], source_reference)
              │
              ▼
       Engine merges into canon → generators/ produce artifacts
```

---

## The Big 7 Vendor Adapters

UIAO's adapter framework covers the seven core vendor systems in the federal modernization stack:

| # | Vendor | Adapter ID | Primary Control Families | Status |
|---|--------|-----------|-------------------------|--------|
| 1 | Microsoft Entra ID | `entra` | AC, IA (Identity) | Implemented |
| 2 | ServiceNow | `servicenow` | CA, SA, PM (GRC) | Implemented |
| 3 | Infoblox | `infoblox` | SC, AC (DNS/IPAM) | Scaffold |
| 4 | CyberArk | `cyberark` | AC, IA (PAM) | Scaffold |
| 5 | Palo Alto | `paloalto` | SC, AC (Boundary) | Scaffold |
| 6 | Cisco | `cisco` | SC, AC (Network) | Scaffold |
| 7 | SD-WAN | `sdwan` | SC (Overlay) | Scaffold |

Each adapter follows the identical four-step pattern. Adding a new vendor means implementing:

1. A **collector** in `src/uiao_core/collectors/<vendor>/`
2. An **adapter** in `src/uiao_core/adapters/<vendor>_adapter.py`
3. A **vendor overlay** in `data/vendor-overlays/<vendor>.yaml`

No generation code changes. No schema changes. The DNS pattern makes vendors swappable.

---

## Key Design Principles

### Adapters Never Own Data

Adapters produce lightweight pointers (vendor-overlay + claim + evidence hash) that the generation engine consumes. They never copy, cache, or store vendor data. SSOT remains in the YAML canon.

### Identity Is the Root Namespace

Every claim is rooted in an identity: `entra:user:abc123`, `snow:incident:INC0012345`, `cyberark:account:sa-prod-01`. This enables deterministic correlation across vendors.

### Evidence Hash for Provenance

Every claim includes a SHA-256 hash of the raw vendor record. This creates an auditable chain from the final OSCAL artifact back to the original vendor event.

### Drift Detection Built In

Each adapter includes a `detect_drift()` method that compares current vendor state against the YAML canon. Drift is reported but never auto-remediated — governance workflows handle the response.

### Schema Discovery

Adapters expose a `discover_schema()` method that maps vendor-specific fields to the canonical UIAO schema. This enables the engine to validate mappings before processing.

---

## File Layout

```
src/uiao_core/
├── adapters/
│   ├── database_base.py          # Base classes: ClaimObject, ClaimSet, DriftReport
│   ├── entra_adapter.py          # Microsoft Entra ID adapter
│   ├── servicenow_adapter.py     # ServiceNow GRC adapter
│   ├── infoblox_adapter.py       # Infoblox DNS/IPAM adapter
│   ├── cyberark_adapter.py       # CyberArk PAM adapter
│   ├── paloalto_adapter.py       # Palo Alto boundary adapter
│   ├── cisco_adapter.py          # Cisco network adapter
│   └── sdwan_adapter.py          # SD-WAN overlay adapter
├── collectors/
│   ├── entra/
│   │   └── entra_collector.py    # Microsoft Graph API collector
│   ├── servicenow/
│   │   └── servicenow_collector.py
│   └── ...                       # One collector per vendor
data/
└── vendor-overlays/
    ├── microsoft.yaml             # Entra overlay spec
    ├── servicenow.yaml            # ServiceNow overlay spec
    └── ...                        # One overlay per vendor
```

---

## Why This Matters for FedRAMP

The DNS-style adapter pattern directly supports FedRAMP Moderate Rev 5 compliance:

- **Continuous monitoring** — Adapters provide real-time evidence collection from vendor systems, not point-in-time snapshots.
- **Automated evidence** — Every claim carries an evidence hash linking back to the vendor record, satisfying OSCAL back-matter requirements.
- **Drift detection** — Continuous validation against the YAML canon catches configuration drift before it becomes a finding.
- **Audit trail** — The provenance chain (vendor API → collector → adapter → claim → generator → OSCAL artifact) is fully traceable.
- **Vendor independence** — The swappable adapter pattern means agencies can replace vendor systems without rebuilding the compliance pipeline.

---

## Related Documents

| Document | Location |
|----------|----------|
| README (summary) | [`README.md`](../README.md#how-adapters-work) |
| Adapter base classes | [`src/uiao_core/adapters/database_base.py`](../src/uiao_core/adapters/database_base.py) |
| Entra adapter (reference impl) | [`src/uiao_core/adapters/entra_adapter.py`](../src/uiao_core/adapters/entra_adapter.py) |
| ServiceNow adapter | [`src/uiao_core/adapters/servicenow_adapter.py`](../src/uiao_core/adapters/servicenow_adapter.py) |
| Vendor overlays | [`data/vendor-overlays/`](../data/vendor-overlays/) |
| KSI enrichment rules | [`rules/ksi/enrichment_rules.py`](../rules/ksi/enrichment_rules.py) |
