---
title: "Phase 4 — AGENTS.md diff"
status: DRAFT
date: 2026-05-15
target: AGENTS.md
---

# AGENTS.md diff — substrate-walker description + public-surface table

Two changes land in [`AGENTS.md`](../../../AGENTS.md):

1. Line 109 — substrate-walker emission description (currently
   understates the surface)
2. The "Public surface" feature table — add rows for the new
   substrate modules introduced in Phases 0–3

## Change 1 — substrate-walker emission description

### Before (line 109)

```markdown
Emits `DRIFT-SCHEMA` (module paths exist) and `DRIFT-PROVENANCE` (registry docs resolve) findings.
```

### After

```markdown
Emits four classes of hygiene findings:

- `DRIFT-SCHEMA` — module paths declared by `substrate-manifest.yaml` resolve
- `DRIFT-PROVENANCE` — canon documents referenced by `document-registry.yaml` resolve; canon prose code-path citations resolve; retired slugs stay retired
- `DRIFT-AUTHZ` — every active adapter declares a non-empty `scope:` (UIAO_110)
- `DRIFT-IDENTITY` — every `certificate-anchored: true` adapter declares a `trust-anchor:` (UIAO_110)

For the **runtime** counterparts of these four classes (plus `DRIFT-SEMANTIC`), see `src/uiao/telemetry/provenance.py` — the same drift_class codes are emitted at adapter emit time with `subkind="runtime"`, validated inline by the four-validator pipeline in `src/uiao/telemetry/validators.py` per ADR-070 / ADR-071 / ADR-072 / ADR-073.
```

### Rationale

The original one-line description listed only two of the four drift
classes the walker actually emits today — the AUTHZ and IDENTITY
hygiene scans (`_scan_consent_envelope`, `_scan_issuer_chain`) shipped
before this phase but aren't documented in AGENTS.md. Phase 4 corrects
the omission and adds the cross-link to the runtime emission surface
so a reader can navigate from "the walker emits X" to "the runtime
sink also emits X with a different subkind."

## Change 2 — Public surface feature table

Add a new section after the existing "Public surface additions (v0.6.0)"
block (line 79 onward). Heading and content:

```markdown
## Public surface additions (v0.7.0)

New library modules introduced by the Runtime Provenance + Drift program (ADR-070 / ADR-071 / ADR-072 / ADR-073). These rows supplement the v0.5.0 / v0.6.0 inventories above.

| Feature | Module | CLI surface | Tier | Notes |
|---|---|---|---|---|
| Provenance envelope (typed) | `uiao.models.provenance` | (library, used by adapters) | Library | ADR-070; promotes `15_ProvenanceProfile.qmd` §3 to pydantic v2 |
| Consent envelope (typed) | `uiao.models.consent` | (library, used by validators) | Library | ADR-072 §4; promotes `17_ConsentEnvelope.qmd` §3 to pydantic v2 |
| Canonical drift finding | `uiao.models.drift_finding` | (library, used by walker + sink + router) | Library | ADR-073; subsumes walker and sink classes; OrgTree engine class stays peer pending Phase 5 |
| Identity-plane resolver | `uiao.identity.resolver` | (library; per-adapter manifest plug-point) | Library | ADR-072 §3; `EntraIDResolver` default, pluggable for Login.gov / PIV / federal IdP |
| Provenance event sink | `uiao.telemetry.provenance` | (library; routed via adapter emit) | Library | ADR-071; runs the four-validator pipeline inline, appends JSONL event log |
| Runtime drift validators | `uiao.telemetry.validators` | (library; constructed per adapter at sink init) | Library | ADR-072; four checks (signature/identity/authz P1; semantic P2 non-blocking) |
| Remediation router | `uiao.governance.router` | (library; wired at substrate boot) | Library | ADR-073; dispatches every finding to halt/fix/flag/log; rule table in `src/uiao/canon/data/remediation-routes.yaml` |
| OSCAL runtime-findings mode | `uiao.generators.oscal` | `uiao oscal generate --include-runtime-findings` | CLI | ADR-073 PR-3b; projects runtime findings as OSCAL Observations under `_UIAO_RUNTIME_NS` |
| Modernization adapter base | `uiao.adapters.base.ModernizationAdapter` | (library; ABC for modernization adapters) | Library | ADR-071; new ABC for the third adapter surface |
```

### Rationale

The existing public-surface tables (v0.5.0 at line 62, v0.6.0 at
line 83) document substrate-level modules. The Runtime Provenance +
Drift program introduces nine new library/CLI surfaces; they need a
corresponding v0.7.0 table so adapter authors and integrators can
discover them.

## Applying

The README footer should also gain a brief note pointing readers to
this table when the next quarterly AGENTS.md review happens. Not in
scope for Phase 4.

After applying, no code paths change. The substrate-drift CI gate
runs against the unchanged walker; the new rows are documentation
only.

## Validation

```bash
# Confirm AGENTS.md still parses (markdown CI gate)
grep -c "Public surface additions" AGENTS.md   # should return 3 after diff applied
```

Existing CI gates (`link-check.yml`, `metadata-validator.yml`) pass —
no schema changes, no broken links (all referenced modules ship in
Phases 0–3).

## A note on version bump

Current version is `0.6.0` in `src/uiao/__version__.py`. Runtime drift
+ continuous capture shipping together is the kind of "genuinely
significant release" that earns an X.Y minor bump rather than a patch
bump — flagging because the default for this repo is patch-first.

The bump is a separate one-line change; not folded into this draft.
Open question: ride the bump with Phase 3 PR-3a (when the engineering
lands) or Phase 4 (when the whitepaper claim lands)? Convention
suggests with the engineering; deferring to your call.
