---
adr: ADR-108
title: "Addressing-Plane Drift Gate and Shared drift_core Primitive"
status: Proposed
date: "2026-06-17"
author: WhalerMike
supersedes: []
superseded_by: null
related:
  - ADR-012   # Canonical drift taxonomy (identity plane)
  - ADR-033   # DRIFT-BOUNDARY extension
  - ADR-072   # Publication-gap gate (pattern reference)
  - ADR-102   # LocPath location addressing
  - ADR-107   # Network AAA adapter registration
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-108-addressing-plane-drift-gate.html
---

# ADR-108: Addressing-Plane Drift Gate and Shared `drift_core` Primitive

## Context

The UIAO substrate governs two coordinate planes — identity (OrgPath, ADR-012)
and addressing (DNS namespace, UIAO_195). The identity-plane drift engine
(`src/uiao/governance/drift.py`) accumulated plane-specific logic that was
implicitly assumed to be universal: the `Finding` tuple, severity tiers,
remediation posture, ODR telemetry event shape, and halt-on-critical gate.

As the addressing-plane collector was built (UIAO_195 §3), it was clear that
duplicating these primitives per-plane would produce divergent semantics and
two incompatible gate policies. A shared primitive is the correct abstraction.

Additionally, the addressing plane had no CI gate at all — DNS drift was
observed informally at best, and the three classes most relevant to federal
boundary compliance (DRIFT-HORIZON, DRIFT-CAA/TLSA, DRIFT-DELEGATION) had
no defined observability requirement.

## Decision

### 1 — `drift_core.py` is the shared plane-agnostic primitive

`src/uiao/governance/drift_core.py` defines:

- `Finding` — the universal finding tuple (`plane`, `name`, `drift_class`,
  `severity`, `posture`, `intended`, `observed`, `evidence_ref`,
  `detected_at`, deterministic `finding_id`).
- `Severity` — `P1` / `P2` / `P3`.
- `Posture` — `never-autofix` / `per-policy` / `informational`.
- `gate(findings)` — halt-on-critical: any P1 blocks. Returns `{"decision":
  "HALT"|"PASS", "counts": {...}, "blocking": [...]}`.
- `events_json(findings)` — serialises all findings as ODR telemetry events.

Every plane's collector imports these and returns plain `Finding` objects.
No plane-specific logic lives in `drift_core`.

### 2 — Addressing-plane collector is registered as a CI gate

`src/uiao/adapters/addressing/addressing_collector.py` runs as a blocking
gate in CI using the file-driven pattern established by
`Invoke-GpoAuditPipeline` and the publication-gap gate (ADR-072):

- **Inputs:** `intended_bindings.json` (SSOT manifest), exported zone records,
  live resource inventory.
- **Gate:** any P1 finding halts the pipeline. `DRIFT-DANGLING`,
  `DRIFT-SRV`, `DRIFT-BINDING` (dead target), and `DRIFT-CONFLICT` are
  always P1.
- **Outputs:** `findings.json` (ODR telemetry events) consumed by the Evidence
  Fabric.

### 3 — Satisfiable vs deferred class split

Nine of the twelve addressing-plane drift classes are satisfiable from a
static zone export and are implemented. Three require live multi-vantage
observation and are declared **Provisional** in UIAO_195:

| Class | Status |
|---|---|
| DRIFT-HORIZON | Provisional — multi-vantage probe not yet built |
| DRIFT-CAA/TLSA | Provisional — endpoint cert inspector not yet built |
| DRIFT-DELEGATION | Provisional — NS delegation walker not yet built |

Provisional classes are in canon and will be classified by the gate once
their observers are built. They do not block the gate today; they will be
promoted to blocking when the observer is available.

### 4 — UIAO_179 `DriftRecord` alignment

`drift_core.Finding.to_event()` emits an ODR event that aligns with the
`DriftRecord` schema (UIAO_179). Callers that need the full `DriftRecord`
shape (object_id, object_facet, recommended_action, correlation_id) wrap
the `Finding` at the orchestration layer; `drift_core` stays minimal.

## Consequences

**Positive:**
- One `gate()` definition, one severity scale, one event shape across all
  planes. Future planes (LocPath drift, AppRef drift) add a collector and
  import `drift_core`; no re-specification of gate semantics.
- Addressing-plane P1 findings halt CI on the same signal as identity-plane
  P1 findings. The substrate cannot pass with a known dangling CNAME or
  missing SRV locator.
- The three deferred classes are canon-documented with their required
  observation, preventing them from being forgotten or silently substituted
  with a faked implementation.

**Negative / constraints:**
- The file-driven pattern requires a zone export step before the gate can
  run. Live DNS observation (for DRIFT-HORIZON) requires a multi-vantage
  probe infrastructure that does not yet exist.
- `drift_core` severity (P1/P2/P3) is coarser than the `DriftRecord`
  severity (critical/high/medium/low / UIAO_179). Mapping: P1 → critical,
  P2 → high, P3 → medium. This is an acceptable simplification at the
  collector layer.

## Implementation notes

```
src/uiao/governance/drift_core.py                 # shared primitive (new)
src/uiao/adapters/addressing/__init__.py           # package registration (new)
src/uiao/adapters/addressing/addressing_collector.py  # gate implementation (new)
src/uiao/adapters/addressing/sample/              # canonical test vectors (new)
src/uiao/canon/UIAO_195_Addressing_Plane_Drift_Taxonomy.md  # taxonomy (new)
src/uiao/canon/adr/adr-108-addressing-plane-drift-gate.md   # this ADR (new)
```

Sample run against the canonical test vector:

```
GATE: HALT   P1=10  P2=7  P3=1
```

Ten P1 findings across the sample zone: 1 DRIFT-BINDING, 5 DRIFT-DANGLING,
2 DRIFT-SRV, 1 DRIFT-CONFLICT — all categories that represent live takeover
exposure or auth-breaking conditions in a production zone.
