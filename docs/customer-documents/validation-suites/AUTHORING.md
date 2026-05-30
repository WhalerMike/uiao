# Authoring Adapter Validation Suite (AVS) stubs

> Contributor runbook — **not** a rendered site page. Quarto renders `**/*.qmd`
> only (see `docs/_quarto.yml`), so this `.md` is harvested by humans, like the
> sibling `IMAGE-PROMPTS.md` files. It explains how to replace the `_TODO_`
> blocks in every adapter validation suite under
> `docs/customer-documents/validation-suites/adapters/<slug>/<slug>.qmd`.

Live section: <https://whalermike.github.io/uiao/customer-documents/validation-suites/>

## 1. What you are filling, and what you must not touch

Each AVS page is **generated** by `scripts/tools/sync_canon.py` from a canon
registry (`src/uiao/canon/adapter-registry.yaml` for conformance adapters,
`src/uiao/canon/modernization-registry.yaml` for modernization adapters). The
generator owns everything down to — and including — the canon banner. You own
everything **below the `## Overview` heading**.

Each stub carries exactly **three `_TODO — …_` blocks**:

| Section | TODO prompt (verbatim intent) |
|---|---|
| `## Overview`  | Author the adapter's role in the UIAO governance perimeter; cross-reference the companion ATS. |
| `## Scope`     | Concrete boundaries — what the adapter reads, emits, and explicitly does not touch. |
| `## Controls`  | Per-control role (primary / supporting / evidence-only); flag aspirational controls as `NEW (Proposed)`. |

The generator also emits, *already populated from canon*, the sections you must
**leave alone**: `## Operational profile`, `## Canon invariants`,
`## Notes from canon`, `## References`, the YAML frontmatter, and the
`Canon-derived document` / `Scaffold` callouts.

### Hard guardrails

1. **Author only below `## Overview`.** Hand-edits to the frontmatter or the
   banner are clobbered on the next `sync_canon.py` run.
2. **Never contradict the canon invariants** printed in the doc
   (`gcc-boundary`, `ssot-mutation: never`, `certificate-anchored`,
   `object-identity-only`). The values shown are authoritative.
3. **No-Hallucination Protocol.** Claim only what canon, the paired ATS, or the
   adapter implementation substantiates. Any capability or control role that is
   planned-but-not-built is marked `NEW (Proposed)` inline.
4. **No new Mermaid.** If a diagram is genuinely needed, use an
   `[IMAGE-NN: <prompt>]` placeholder per the repo's image pipeline; do not add
   ```` ```mermaid ```` blocks.
5. **Keep cross-links valid** for the `link-check.yml` gate (see §4).

## 2. The primary source: the paired ATS

Every AVS pairs 1:1 by slug with an **Adapter Technical Specification (ATS)**
under `docs/customer-documents/adapter-specs/<slug>/<slug>.qmd`. As of this
writing **44 of 45 ATS docs are fully authored** with exactly the prose you
need — an authored `## Overview`, a `## Scope` broken into Reads / Emits /
Does-NOT, and a `## Controls` table (Control · Role · capability).

So filling an AVS is **source-driven, not invented**: derive each block from the
paired ATS, then reframe it for the validation audience (assessors, adapter
owners, ATO packagers — see the section landing page frontmatter).

> **Exception — `surface-management-portal`.** Its ATS is *also* a stub, so
> there is no upstream prose. Fill that AVS from the registry facts only
> (surfaces, controls, invariants, notes already in the generated sections), or
> mark it blocked pending ATS authoring. Do not invent capabilities.

## 3. Per-block recipe

### `## Overview`

Reframe the ATS overview from a **conformance / assessment** angle — not a
copy-paste. State what the suite *proves* about the adapter's role in the
governance perimeter, and link to the companion ATS. Stay consistent with the
printed invariants (e.g. an `ssot-mutation: never` adapter is read-only or
write-gated; say so).

### `## Scope`

The generator prints the target surfaces. Convert the ATS Reads / Emits /
Does-NOT boundaries into **what the suite validates**: the surfaces under test,
the evidence the suite expects each to emit, and what is explicitly out of
scope. Mirror the ATS "Does NOT" list so the validation boundary matches the
spec boundary exactly.

### `## Controls`

The generator prints the NIST SP 800-53 Rev 5 control IDs. Reuse the paired
ATS Controls table (Control · Role · capability), **verifying each Role against
canon**. Mark any control whose role the ATS/implementation does not
substantiate as `NEW (Proposed)`. Use the table shape the ATS already uses:

```markdown
| Control | Role | Validation evidence |
|---|---|---|
| **CM-8** Information System Component Inventory | Primary | Suite asserts the survey output enumerates every in-scope object as canonical inventory rows with stable identifiers. |
```

### Optional: make it a *true* validation suite

The section index promises **Test cases · Evidence expectations · Drift
procedures**, and the six already-authored domain suites under `domains/`
demonstrate the shape (`## Test categories` → Schema conformance, Provenance
chain integrity, Drift detection coverage, Boundary enforcement). Adding those
sections is beyond the literal `_TODO_` blocks but is the right next increment
once the three blocks are filled. Model them on the domain suites and tie drift
classes to the five-class taxonomy (`DRIFT-SCHEMA`, `DRIFT-SEMANTIC`,
`DRIFT-PROVENANCE`, `DRIFT-AUTHZ`, `DRIFT-IDENTITY`).

## 4. Cross-link path

From an AVS at
`docs/customer-documents/validation-suites/adapters/<slug>/<slug>.qmd`, the
companion ATS is **three levels up**:

```markdown
[companion ATS](../../../adapter-specs/<slug>/<slug>.html)
```

This is the same depth the domain suites already use to reach the modernization
specs, so it satisfies `link-check.yml`.

## 5. Worked example — `active-directory`

The `active-directory` AVS lists surfaces `ou-objects`, `user-objects`,
`computer-objects`, `orgpath-attributes`, `group-policy-objects` and controls
`CM-8`, `IA-2`, `IA-4`, `AC-2`, `AC-6`. Its paired ATS
(`adapter-specs/active-directory/active-directory.qmd`) is fully authored and
supplies all three blocks. The fill is:

- **Overview** → "This suite validates the on-premises survey (Phase F.1,
  read-only) and OrgPath write-back (Phase F.3, gated on `dry_run=False`) of the
  AD adapter, confirming OrgPath values propagate to Entra ID via Entra Connect
  and that no direct Graph writes occur. See the
  [companion ATS](../../../adapter-specs/active-directory/active-directory.html)."
  — consistent with `ssot-mutation: never` and `object-identity-only: true`.
- **Scope** → restate the ATS Reads (LDAP OU/user/computer/GPO),
  Emits (the `*-orgpath-*.csv` / `orgpath-assignment-report.json` artifacts the
  suite checks for), and Does-NOT (no OU/trust/GPO mutation, no Graph writes) as
  validation boundaries.
- **Controls** → carry over the ATS table; `CM-8`/`IA-4` are Primary,
  `IA-2`/`AC-2`/`AC-6` are Supporting. None are aspirational, so no
  `NEW (Proposed)` flag is needed here.

## 6. Pre-flight checklist before opening a PR

- [ ] Edited **only** below `## Overview`; frontmatter and banner untouched.
- [ ] No claim contradicts the printed canon invariants.
- [ ] Aspirational controls/capabilities flagged `NEW (Proposed)`.
- [ ] ATS cross-link uses the `../../../adapter-specs/<slug>/<slug>.html` form.
- [ ] No new `mermaid` blocks.
- [ ] `surface-management-portal` filled from registry only, or marked blocked.
