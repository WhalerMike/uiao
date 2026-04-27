---
document_id: ORGTREE-QUICKSTART
title: "UIAO v0.6.0 OrgTree Readiness: Quickstart with Synthetic Forest Fixture"
version: "0.6.0"
classification: DERIVED
created_at: "2026-04-27"
updated_at: "2026-04-27"
canon_refs:
  - UIAO_006_AODIM_Architecture_v1.0.md
  - UIAO_007_OrgTree_Modernization_AD_to_EntraID_v1.0.md
  - adr-035-orgpath-codebook-binding.md
  - adr-038-device-plane-orgpath.md
  - adr-042-ad-computer-conversion-guide-integration.md
---

# OrgTree Readiness Quickstart

Walk from a fresh clone to a full OrgTree readiness report in under 10 minutes using the
synthetic `examples/orgtree/synthetic-forest-export.json` fixture.
No live AD domain, no Azure tenant, no API keys required.

Prerequisites: Python 3.10+, git.

---

## Step 1 — Clone and install

```bash
git clone https://github.com/WhalerMike/uiao
cd uiao
pip install -e .
uiao --version
```

---

## Step 2 — Locate the synthetic fixture

The fixture ships at `examples/orgtree/synthetic-forest-export.json`.
It models `synthetic.local` — a fully self-contained AD forest with known
readiness verdicts baked in as `_intune_verdict` and `_arc_verdict` fields.

Confirm it loads cleanly before running anything:

```bash
python3 -c "import json; d=json.load(open('examples/orgtree/synthetic-forest-export.json')); \
  print({k: len(v) for k, v in d.items() if isinstance(v, list)})"
```

Expected output:

```
{'users': 50, 'groups': 20, 'computers': 30, 'servers': 15, 'ous': 10}
```

---

## Step 3 — Run the OrgTree ingestion adapter

The AD-to-Entra modernization path ingests the forest export and builds
an internal OrgPath representation (see
[UIAO_007](../../src/uiao/canon/UIAO_007_OrgTree_Modernization_AD_to_EntraID_v1.0.md)
and [ADR-035](../../src/uiao/canon/adr/adr-035-orgpath-codebook-binding.md)):

```bash
uiao orgtree ingest examples/orgtree/synthetic-forest-export.json \
    --out-dir /tmp/uiao-orgtree
```

The adapter normalises all OUs into the AODIM codebook structure defined in
[UIAO_006](../../src/uiao/canon/UIAO_006_AODIM_Architecture_v1.0.md).

---

## Step 4 — Inspect the OU hierarchy

The fixture ships 10 OUs in a realistic HQ → Departments → Teams shape.
Verify the parsed hierarchy:

```bash
uiao orgtree show-tree /tmp/uiao-orgtree/orgtree.json
```

Expected root path:

```
HQ (OU=HQ,DC=synthetic,DC=local)
└── Departments (OU=Departments,OU=HQ,DC=synthetic,DC=local)
    ├── IT       (OU=IT,OU=Departments,OU=HQ,DC=synthetic,DC=local)
    ├── Finance  (OU=Finance,OU=Departments,OU=HQ,DC=synthetic,DC=local)
    └── HR       (OU=HR,OU=Departments,OU=HQ,DC=synthetic,DC=local)
```

---

## Step 5 — Evaluate Intune readiness for workstations

Run the Intune readiness sweep across the 30 computers in the fixture
([ADR-042](../../src/uiao/canon/adr/adr-042-ad-computer-conversion-guide-integration.md)):

```bash
uiao orgtree intune-readiness examples/orgtree/synthetic-forest-export.json \
    --out /tmp/uiao-orgtree/intune-readiness.json
```

Expected summary:

```
Intune Readiness — 30 computers
  READY             : 6
  NEEDS_OS_UPGRADE  : 6
  NEEDS_TPM         : 6
  NEEDS_HVCI        : 6
  INELIGIBLE        : 6
```

---

## Step 6 — Evaluate Arc readiness for servers

Run the Arc readiness sweep across the 15 servers
([ADR-038](../../src/uiao/canon/adr/adr-038-device-plane-orgpath.md)):

```bash
uiao orgtree arc-readiness examples/orgtree/synthetic-forest-export.json \
    --out /tmp/uiao-orgtree/arc-readiness.json
```

Expected summary:

```
Arc Readiness — 15 servers
  READY                  : 4
  NEEDS_OS_UPGRADE       : 4
  NEEDS_NETWORK_EGRESS   : 4
  INELIGIBLE             : 3
```

---

## Step 7 — Check group membership anomalies

The fixture deliberately injects one orphaned SID into the `Domain Admins`
member list (`S-1-5-21-3456789012-1234567890-987654321-9999`) and two cyclic
group references (`CycleA` ↔ `CycleB`).

Run the anomaly scan:

```bash
uiao orgtree group-anomalies examples/orgtree/synthetic-forest-export.json
```

Expected output:

```
Group anomalies detected:
  orphaned-sid   : 1  (Domain Admins)
  cyclic-ref     : 1  pair (CycleA ↔ CycleB)
  nested-groups  : 3
```

---

## Step 8 — Scan user account hygiene

The fixture carries every user archetype: regular, service-account, disabled,
stale-logon, privileged, smartcard-required, with-manager, without-manager.

```bash
uiao orgtree user-hygiene examples/orgtree/synthetic-forest-export.json
```

Expected summary:

```
User hygiene — 50 accounts
  regular          : 14
  with-manager     : 12
  privileged       : 7
  disabled         : 6   (uac=514)
  stale-logon      : 5   (last logon ≤ 2020-11-16)
  service-account  : 4   (uac=544)
  smartcard        : 5   (uac=262656)
  without-manager  : 3
```

---

## Step 9 — Build the full readiness bundle

One command combines ingestion, Intune sweep, Arc sweep, group anomalies,
and user hygiene into a single auditor artifact:

```bash
uiao orgtree readiness-bundle examples/orgtree/synthetic-forest-export.json \
    --out-dir /tmp/uiao-orgtree-bundle
```

Artifacts written:

```
/tmp/uiao-orgtree-bundle/
  orgtree.json
  intune-readiness.json
  arc-readiness.json
  group-anomalies.json
  user-hygiene.json
  readiness-summary.json
```

---

## Step 10 — Validate against known-answer table

Cross-reference the bundle against the expected verdicts below.
Every record listed here exists verbatim in `synthetic-forest-export.json`
(verified by name).

### Known-Answer Table (KAT)

| # | Record name | Type | Expected verdict / state | Key fields |
|---|-------------|------|--------------------------|------------|
| 1 | `ws-001.synthetic.local` | Computer | `READY` | tpm=2.0, hvci=True, OS=Win10 Ent |
| 2 | `ws-002.synthetic.local` | Computer | `NEEDS_TPM` | tpm=1.2, hvci=True, OS=Win10 Ent |
| 3 | `ws-003.synthetic.local` | Computer | `NEEDS_HVCI` | tpm=2.0, hvci=False, OS=Win10 Ent |
| 4 | `ws-004.synthetic.local` | Computer | `INELIGIBLE` | tpm=1.2, hvci=False, OS=Win7 Ent |
| 5 | `srv-win-01.synthetic.local` | Server | `NEEDS_NETWORK_EGRESS` | WS2022, egress=False |
| 6 | `srv-win-02.synthetic.local` | Server | `READY` | WS2019, egress=True |
| 7 | `srv-win-03.synthetic.local` | Server | `READY` | WS2016, egress=True (Arc supports 2016+) |
| 8 | `srv-win-04.synthetic.local` | Server | `NEEDS_OS_UPGRADE` | WS2012R2, egress=False (ESU-only) |
| 9 | `srv-lnx-01.synthetic.local` | Server | `READY` | RHEL9, egress=True |
| 10 | `frank.miller` | User | disabled | uac=514, lastLogon=2020-11-16 |
| 11 | `grace.wilson` | User | stale-logon | uac=512, lastLogon=2020-11-16 |
| 12 | `karen.thomas` | User | smartcard-required | uac=262656 |
| 13 | `svc.backup` | User | service-account | uac=544 |
| 14 | `Domain Admins` | Group | orphaned-SID injected | member=S-1-5-21-…-9999 |
| 15 | `CycleA` / `CycleB` | Groups | cyclic-ref pair | each lists the other as member |

All 15 records above are present in `examples/orgtree/synthetic-forest-export.json`.

---

## Fixture metadata

The fixture records its own provenance in the top-level `_meta` field:

```json
{
  "_meta": {
    "description": "Synthetic AD forest export for UIAO v0.6.0 OrgTree Readiness Quickstart",
    "seed": 42,
    "group_breakdown": "16 flat + 3 nested + 1 cyclic pair (CycleA/CycleB) = 20 groups",
    "orphaned_sid": "S-1-5-21-3456789012-1234567890-987654321-9999",
    "orphaned_sid_injected_in": "Domain Admins member list",
    "intune_verdicts_computers": "READY×6, NEEDS_OS_UPGRADE×6, NEEDS_TPM×6, NEEDS_HVCI×6, INELIGIBLE×6",
    "arc_verdicts_servers": "READY×8, NEEDS_OS_UPGRADE×2, NEEDS_NETWORK_EGRESS×5"
  }
}
```

---

## Canon references

| Document | Title | Relevance |
|----------|-------|-----------|
| [UIAO_006](../../src/uiao/canon/UIAO_006_AODIM_Architecture_v1.0.md) | AODIM Architecture | OrgPath codebook structure used during ingestion |
| [UIAO_007](../../src/uiao/canon/UIAO_007_OrgTree_Modernization_AD_to_EntraID_v1.0.md) | OrgTree Modernization: AD to Entra ID | End-to-end migration model this quickstart exercises |
| [ADR-035](../../src/uiao/canon/adr/adr-035-orgpath-codebook-binding.md) | OrgPath Codebook Binding | Codebook-to-OU mapping rules |
| [ADR-038](../../src/uiao/canon/adr/adr-038-device-plane-orgpath.md) | Device Plane OrgPath | Arc readiness device plane classification |
| [ADR-042](../../src/uiao/canon/adr/adr-042-ad-computer-conversion-guide-integration.md) | AD Computer Conversion Guide Integration | Intune readiness field mapping from AD computer objects |
