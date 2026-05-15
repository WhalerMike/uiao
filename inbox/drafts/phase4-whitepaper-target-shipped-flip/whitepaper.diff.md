---
title: "Phase 4 — uiao-governance-os-whitepaper.qmd diff"
status: DRAFT
date: 2026-05-15
target: docs/customer-documents/whitepapers/uiao-governance-os-whitepaper.qmd
---

# Whitepaper diff — three sections

Three changes land in this PR, all to
[`uiao-governance-os-whitepaper.qmd`](../../../docs/customer-documents/whitepapers/uiao-governance-os-whitepaper.qmd):

1. §3 substrate-stack table — flip the two TARGET rows to SHIPPED
2. §8 "What this is not" — retire the runtime-drift-is-design-only bullet
3. §10 Conclusion — drop the "what is target state" sentence

All other content stays as-is.

## Change 1 — §3 substrate-stack table

### Before (lines 113–120)

```markdown
| Surface | Mechanism | Maturity |
|---|---|---|
| Schema-first canon | Five JSON schemas under `src/uiao/schemas/`, validated by `schema-validation.yml` and `metadata-validator.yml` | **SHIPPED** |
| Substrate walker | `uiao substrate walk` / `uiao substrate drift` — emits `DRIFT-SCHEMA` and `DRIFT-PROVENANCE` per `substrate-drift.yml` | **SHIPPED** |
| Adapter taxonomy | `class` × `mission-class` per UIAO_003, registered in two registries, validated by `adapter-conformance.yml` | **SHIPPED** |
| OSCAL evidence | SSP, POA&M, KSI, Component Definition generators with deterministic regeneration per ADR-006 | **SHIPPED** |
| Runtime drift (semantic / authz / identity) | Defined in `16_DriftDetectionStandard.qmd` | **TARGET / DESIGN-ONLY** |
| Continuous event-time evidence capture | Defined in `15_ProvenanceProfile.qmd` | **TARGET** |
```

### After

```markdown
| Surface | Mechanism | Maturity |
|---|---|---|
| Schema-first canon | Five JSON schemas under `src/uiao/schemas/`, validated by `schema-validation.yml` and `metadata-validator.yml` | **SHIPPED** |
| Substrate walker | `uiao substrate walk` / `uiao substrate drift` — emits `DRIFT-SCHEMA`, `DRIFT-PROVENANCE`, `DRIFT-AUTHZ`, `DRIFT-IDENTITY` hygiene findings per `substrate-drift.yml` | **SHIPPED** |
| Adapter taxonomy | `class` × `mission-class` per UIAO_003, registered in two registries, validated by `adapter-conformance.yml` | **SHIPPED** |
| OSCAL evidence | SSP, POA&M, KSI, Component Definition generators with deterministic regeneration per ADR-006 | **SHIPPED** |
| Runtime drift (semantic / authz / identity) | `uiao.telemetry.provenance` sink runs the four-validator pipeline (`uiao.telemetry.validators`) inline at adapter emit per ADR-070 / ADR-071 / ADR-072 | **SHIPPED** |
| Continuous event-time evidence capture | Append-only JSONL provenance event log under `evidence/provenance/<adapter>/<yyyy-mm>/*.jsonl`; OSCAL bundles regenerable from event history per ADR-071 §3 | **SHIPPED** |
```

### Rationale for the text changes (not just the maturity flip)

- The substrate-walker row now lists all four hygiene drift classes
  it actually emits today (per [`walker.py`](../../../src/uiao/substrate/walker.py) — `_scan_consent_envelope` emits AUTHZ, `_scan_issuer_chain` emits IDENTITY, both shipped before this phase). The original row understated the surface.
- The runtime-drift row's mechanism column now points to the concrete
  modules (`uiao.telemetry.provenance` + `uiao.telemetry.validators`)
  and the ADR chain — so a reader can find the engineering, not just
  the status.
- The continuous-capture row names the JSONL event log path so the
  artifact is locate-able without chasing references.

## Change 2 — §8 "What this is not"

### Before (lines 217–227)

```markdown
### 8. What this is *not*

Three honest limits:

- It is not a replacement for the underlying control catalog.
  UIAO maps to NIST 800-53, FedRAMP CR26, and CISA ZTMM — it does not
  redefine the controls.
- It is not a runtime enforcement engine for every drift class today.
  Schema and provenance drift ship in CI; semantic, authorization, and
  identity drift detection at runtime is TARGET / DESIGN-ONLY.
- It is not a vendor product. The substrate ships as the `uiao` Python
  package; agencies host it. There is no SaaS dependency in the canon
  layer.
```

### After

```markdown
### 8. What this is *not*

Three honest limits:

- It is not a replacement for the underlying control catalog.
  UIAO maps to NIST 800-53, FedRAMP CR26, and CISA ZTMM — it does not
  redefine the controls.
- It is not a fully-populated auto-remediation surface. The
  `RemediationRouter` (ADR-073) dispatches every finding to a
  `halt` / `fix` / `flag` / `log` handler, but adapter-specific
  apply() functions backing the `fix` handler are still being
  registered one adapter at a time. Until full coverage, the `fix`
  handler demotes deterministically to `flag` — every finding still
  lands in POA&M, but auto-remediation coverage is partial.
- It is not a vendor product. The substrate ships as the `uiao` Python
  package; agencies host it. There is no SaaS dependency in the canon
  layer.
```

### Rationale

The original second bullet asserted the runtime drift surface as
TARGET / DESIGN-ONLY — that statement is now false. Replacing it with
"auto-remediation coverage is partial" is the honest version of the
new limit: detection is shipped; the *fix* action's coverage is
adapter-by-adapter. This preserves §8's role as the substrate's
honesty section without pretending the program is finished.

## Change 3 — §10 Conclusion

### Before (lines 254–263)

```markdown
### 10. Conclusion

The Governance OS is the operational answer to the question *"how do we
keep canon, evidence, and runtime tied together as the substrate
evolves?"* The answer is: declare canon once, anchor evidence to it,
detect drift explicitly, and run the whole thing as an OS rather than as
a reporting layer.

What ships today is enough to anchor real ATO packages. What is target
state extends the same model to runtime drift and continuous event-time
evidence. The structural floor is in place; the rest is engineering on
the same canonical foundation.
```

### After

```markdown
### 10. Conclusion

The Governance OS is the operational answer to the question *"how do we
keep canon, evidence, and runtime tied together as the substrate
evolves?"* The answer is: declare canon once, anchor evidence to it,
detect drift explicitly, and run the whole thing as an OS rather than as
a reporting layer.

What ships today is enough to anchor real ATO packages — at the
schema-first canon floor, at the substrate walker's PR-time hygiene
gate, at the runtime sink's emit-time validation, and at the OSCAL
pipeline's event-log-aware bundle assembly. The structural floor and
its runtime extension are both in place. What remains is
adapter-by-adapter retrofit of auto-remediation, not substrate-level
gaps.
```

### Rationale

The original closing paragraph framed the runtime drift + continuous
capture surfaces as future work. After Phase 3, that framing is
incorrect; the conclusion now reflects the actual end state — shipped
floor + shipped runtime, with the remaining work being adapter-side,
not substrate-side.

## Applying

Each change is a localized substring replacement. The PR is a single
file edit; no other sections of the whitepaper change. Quarto render
should produce a clean PDF / HTML / DOCX with the new table maturity
column.

## Validation

After applying:

```bash
quarto render docs/customer-documents/whitepapers/uiao-governance-os-whitepaper.qmd --to html
# Verify §3 table renders with SHIPPED on every row
# Verify §8 second bullet shows the new auto-remediation framing
# Verify §10 closing paragraph drops the "what is target state" sentence
```

CI gates (`quarto.yml`, `link-check.yml`) should pass — no links change.
