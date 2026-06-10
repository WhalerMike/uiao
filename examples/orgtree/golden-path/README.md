# OrgPath Governance Golden Path — sample data

A small, self-contained dataset that drives the OrgPath wedge end-to-end with
**no live AD, no Azure tenant, and no API keys**. Run it from a fresh clone:

```bash
pip install -e .
examples/orgtree/golden-path/run.sh        # artifacts land in ./out (gitignored)
```

The narrated walkthrough — what each step proves and why a buyer cares — lives at
[`docs/docs/orgpath-golden-path.qmd`](../../../docs/docs/orgpath-golden-path.qmd).
This README is the data dictionary: what each file seeds and the known-answer it
produces.

## The four stages

| # | Command | Plane | Input file(s) here | Output |
|---|---|---|---|---|
| 1 | `uiao orgtree assess` | Identity (AD users) | `ad-users.json` | per-user OrgPath facet derivation + findings |
| 2 | `uiao orgtree inventory` | Device (Entra + Arc) | `entra-devices.json`, `arc-machines.json`, `owner-map.json` | capture status + backfill worklist + a `govern`-compatible snapshot |
| 3 | `uiao orgtree govern` | Governance loop | step-2 snapshot | drift findings + UIAO_174 telemetry (dry-run, halt-on-critical) |
| 4 | `uiao ir orgtree-readiness-bundle` | Evidence | `../synthetic-forest-export.json` | signed bundle (`bundle.{json,hash,sig}`) + OSCAL Assessment Results |

Stage 4 reuses the larger committed `examples/orgtree/synthetic-forest-export.json`
as its AD survey input rather than duplicating a forest here.

## Data dictionary + known answers

Each record carries an inline `_note` / `_seed` field explaining what it
exercises. The deterministic outcomes the smoke test
(`tests/test_orgpath_golden_path.py`) pins:

### `ad-users.json` — 5 users (identity plane)

| User | Seeds | Expected |
|---|---|---|
| `alice.eng` | Engineering / Senior Engineer / Reston / Employee | clean — every source attribute aliases to a codebook value |
| `bob.fin` | Finance / Director / Washington / Contractor | clean — Director, NCR region, Contractor |
| `dana.hr` | Human Resources / HR Manager / Seattle / Employee | clean — "Human Resources" → HR, Seattle → WESTUS |
| `carol.unknown` | Astrophysics / Wizard / Mars / Visitor | **seeded drift** — department/title/region/classification have no alias; `assess` emits findings, falls back to defaults where one exists |
| `svc.backup` | uAC 544, no title | service account — `userAccountControl` drives `derive_account_type`; empty title → role default |

`assess` derives **37 facet values** across the 5 users and emits **13 findings**
(unmapped source values + facets with no AD source and no default).

### `entra-devices.json` + `arc-machines.json` — 6 devices (device plane)

A spectrum of OrgPath capture states so the inventory verdict is legible:

| Device | Plane | Seeds | Capture status |
|---|---|---|---|
| `WS-ENG-01` | Entra | 5 slots populated | partial |
| `WS-FIN-02` | Entra | 1 slot (department) | partial |
| `WS-HR-03` | Entra | empty, owner `dana.hr` | absent → **fully resolved** by owner-map |
| `WS-ORPHAN-04` | Entra | empty, no owner | absent → unresolved (manual review) |
| `SRV-DB-01` | Arc | 2 tags | partial → unresolved (no asset-map) |
| `SRV-APP-02` | Arc | no tags | absent → unresolved (no asset-map) |

`inventory` reports **3 partial, 3 absent, 6 needing backfill, 1 resolved**
(`WS-HR-03`, because `dana.hr`'s owner-map entry covers all 10 missing facets).
The rest stay unresolved — Arc machines have no `registeredOwners`, so without an
`--asset-map` they bucket for manual review. That is the honest outcome of a
partial backfill source, not a failure.

### `owner-map.json` — backfill source

Registered-owner id → proposed facets. A device is **resolved** only when the
proposal covers *every* missing facet, so `dana.hr` carries a full 10-facet set
(fully resolves `WS-HR-03`) while `alice.eng` / `bob.fin` carry partial sets
(proposals land, gaps remain).

### Stage 3 — `govern` on the inventory snapshot

The snapshot carries each device's *current* slots only; missing OrgPath is
simply absent, so the governance pass re-confirms every gap as drift. The pass
**halts on a critical (P1) finding** and runs **dry-run** — it plans nothing and
writes nothing. Exact severity counts depend on the canonical codebook
(UIAO_151); the smoke test asserts the invariants (drift present, P1 present,
`halted=True`, `dry_run=True`) rather than brittle totals.

### Stage 4 — signed bundle + OSCAL

Writes `bundle.json` (schema-validated), `bundle.hash` (SHA-256), `bundle.sig`
(HMAC-SHA256), and `oscal/orgtree-evidence.json` (OSCAL Assessment Results).

> **`--insecure-dev-key` is for this offline demo only.** A real run sets
> `UIAO_BUNDLE_HMAC_KEY` and drops the flag so the signature is meaningful.

## Canon

UIAO_151 (OrgPath codebook), UIAO_163 / UIAO_174 (governance runtime +
telemetry), ADR-078 (15-facet Model C), ADR-084 (Phase 5 consumers).
