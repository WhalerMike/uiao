---
id: ADR-045
title: "OrgPath Hierarchy Depth Extension — 4 Levels to 8 Levels"
status: accepted
date: 2026-04-26
deciders:
  - governance-steward
  - identity-engineer
supersedes: []
related_adrs:
  - ADR-035
  - ADR-037
  - ADR-038
canon_refs:
  - MOD_A_OrgPath_Codebook
  - MOD_H_OrgPath_JSON_Schema
  - UIAO_007_OrgTree_Modernization_AD_to_EntraID
---

# ADR-045: OrgPath Hierarchy Depth Extension — 4 Levels to 8 Levels

## Status

Accepted

## Context

[ADR-035](adr-035-orgpath-codebook-binding.md) bound the OrgPath codebook
(MOD_A) to executable canon and pinned the canonical regex
`^ORG(-[A-Z0-9]{2,6}){0,4}$` across the codebook, the JSON Schema
(`src/uiao/schemas/orgpath/codebook.schema.json`), the device-plane ARM
tag regex (MOD_C / ADR-038), the dynamic-group / admin-unit /
policy-target schemas, and the Python loader (`Codebook.regex`).
ADR-038 cemented the cross-canon agreement check at codebook load time,
so the depth bound is enforced at five places that must move in
lock-step.

The 4-segment cap chosen in MOD_A v1.0 was framed as "prevents excessive
fragmentation while allowing meaningful hierarchy." Field experience and
agency review since then have shown the cap to be the wrong bound for
the substrate's target deployments:

1. **Federal department structures routinely run 6–8 levels deep.**
   Department → Sub-agency → Bureau → Office → Division → Branch →
   Section → Team is a common skeleton (Treasury, HHS, DHS components),
   and the substrate's GCC-Moderate audience overwhelmingly targets
   exactly these structures.
2. **Military command lineages also exceed 4 levels.** Major Command →
   Numbered Air Force → Wing → Group → Squadron → Flight → Element is
   a 7-segment chain that the current schema cannot represent without
   collapsing distinctions that drive RBAC and AU delegation.
3. **The 4-segment cap forces premature collapse.** Deployments with
   real depth either flatten the tree (losing governance signal at the
   collapsed levels) or push the discriminator into a sibling
   attribute (defeating the point of OrgPath as the SSOT for
   `extensionAttribute1`).
4. **Existing codes remain valid under a wider bound.** Every code
   shipped in `canon/data/orgpath/codebook.yaml` is ≤ 5 segments
   today; widening the bound is purely additive at the data layer.

The "fragmentation" rationale was real but addressed the wrong control
surface. Fragmentation is governed by the codebook-membership check
(Value Drift, MOD_A §Drift) and by the `OrgPath Registration` workflow
(MOD_E Workflow 1) — not by the regex bound. The regex bounds *format*,
not *adoption*; tightening it past the actual hierarchical reality
forces real deployments to defeat governance rather than work with it.

The extensionAttribute1 storage limit (1024 chars in Entra ID) is not
binding at any plausible depth. An 8-segment OrgPath at the maximum
6-character segment width fits in 56 characters.

## Decision

1. **Extend the canonical OrgPath regex from `{0,4}` to `{0,8}`.**
   The new canonical pattern is `^ORG(-[A-Z0-9]{2,6}){0,8}$`. Segment
   character class, segment width (2–6), root token (`ORG`), and
   separator (`-`) are unchanged.
2. **Bump `format.max_depth` in the executable codebook from 4 to 8**
   (`src/uiao/canon/data/orgpath/codebook.yaml`) and lift the
   `format.max_depth` const + the per-entry `level` maximum + the
   per-entry `parent` regex in the codebook schema accordingly. The
   `parent` regex still bounds at one fewer segment than `code`
   (`{0,7}`).
3. **Propagate the regex change to every cross-canon copy** so the
   ADR-038 agreement check continues to load:
   - `src/uiao/canon/data/orgpath/device-planes.yaml` (`arm_tag.value_regex`)
   - `src/uiao/schemas/orgpath/dynamic-groups.schema.json`
   - `src/uiao/schemas/orgpath/admin-units.schema.json`
   - `src/uiao/schemas/orgpath/policy-targets.schema.json`
   - `src/uiao/modernization/orgtree/codebook.py` (`CANONICAL_REGEX`)
   - `src/uiao/governance/drift.py` (`_ORGPATH_REGEX` + the format-fail
     diagnostic string)
   - `src/uiao/adapters/entra_adapter.py` (`_ORGPATH_REGEX`)
   - `src/uiao/adapters/modernization/active_directory/orgpath.py`
     (`ORGPATH_REGEX`)
   - `src/uiao/adapters/modernization/active_directory/survey.py`
     (the `{1,4}` candidate-derivation bound becomes `{1,8}`)
4. **Restate MOD_A and MOD_H with the new bound and an extended
   level table.** Levels 0–4 keep their current naming (Root /
   Division / Department / Unit / Team). Levels 5–8 are reserved as
   *governed sub-team strata* — the canon names them Sub-Team,
   Cell, Crew, Squad — but each deployment is free to overload the
   labels via the codebook's `description` field. The level taxonomy
   is descriptive prose, not a schema constraint beyond `0 ≤ level ≤ 8`.
5. **Bump MOD_A from v2.0 to v3.0 and MOD_H from v1.0 to v2.0** to
   record the schema-fixity exception. Per MOD_001 Principle 2
   (Schema Fixity), schema changes require a governed PR; this ADR
   is the governance record.
6. **Existing codes are unchanged.** No code in
   `canon/data/orgpath/codebook.yaml` migrates. Existing dynamic
   groups, AUs, and policy targets continue to validate. The change
   is additive at the data layer.

The `[A-Z]`-only (legacy) regex copies in `MOD_F`, `MOD_I`, `MOD_K`,
`MOD_V`, `MOD_H`, `governance/drift.py`, and the AD adapter family
remain alpha-only on this PR — only the depth bound moves.
Reconciling alpha-only vs `[A-Z0-9]` is pre-existing drift that
predates this ADR; promoting the alphanumeric form everywhere is left
to a follow-on ADR so the depth change can land without entangling a
second character-class doctrine question.

## Consequences

**Positive**

- Federal-agency and military-command hierarchies become
  natively representable. No collapsed levels, no governance signal
  pushed into sibling attributes.
- The codebook integrity check (`_validate_integrity`) continues to
  enforce parent linkage at every level, so the wider bound does not
  weaken Hierarchy Drift detection — it just allows the chain to
  extend further before the leaf.
- `parent_of` chains can recurse 8 levels; the drift engine's
  Phantom Drift / Value Drift classifiers are unaffected (they operate
  on set membership, not depth).
- The cross-canon agreement check at `device_planes.py:_validate_integrity`
  still fires on any divergence between the codebook's `format.regex`
  and `arm_tag.value_regex` — the new value just has to land in both
  places, which this ADR mandates.

**Negative / deferred**

- Real-world deployments that previously flattened deep hierarchies
  to fit the `{0,4}` cap may want to re-introduce the collapsed
  levels. That is a per-deployment codebook PR, not a substrate
  change, but the migration story for those deployments is
  unspecified by this ADR.
- The `[A-Z]` vs `[A-Z0-9]` legacy drift (pre-existing) remains.
  Anyone search-and-replacing `{0,4}` → `{0,8}` should not
  simultaneously normalize the character class without a second ADR.
- MOD_A's level-name table (Sub-Team / Cell / Crew / Squad for
  levels 5–8) is descriptive prose chosen for a federal/military
  deployment audience. Other audiences may prefer different labels;
  the codebook `description` field is the per-code escape valve.

**Neutral**

- No data migration. Existing codebook entries keep their levels.
- No CLI or API surface change. The wider bound is invisible to
  consumers that do not author OrgPaths beyond depth 4.
- The `extensionAttribute1` storage attribute is unaffected — it
  has always allowed 1024 characters.

## Alternatives considered

1. **Raise the bound to 6 instead of 8.** Rejected — 6 covers most
   federal civilian agencies but truncates military command chains
   and large multinational enterprises. Choosing the maximum
   plausible depth once is cheaper than re-amending in a year.
2. **Make `max_depth` per-deployment configurable in the codebook
   header** (e.g. tenant-shaped codebooks). Rejected — cuts against
   MOD_001 Principle 7 (Tenant Agnosticism) and complicates the
   ADR-038 cross-canon agreement check.
3. **Introduce a secondary attribute for "deep" org-chart leaves**
   (extensionAttribute1 stays 4 levels, extensionAttribute2 carries
   the tail). Rejected — defeats OrgPath's role as the single
   discriminator for dynamic group rules; Entra ID dynamic membership
   syntax cannot natively concatenate across attributes, so any
   "deep" rule would require server-side filtering.
4. **Keep `{0,4}` and sharpen the doctrine** ("OrgPath models
   *governance scope*, not *reporting hierarchy*"). Rejected — the
   substrate's actual federal deployments need governance scope at
   levels deeper than 4 (Branch and Section RBAC are common
   delegation surfaces).
5. **Leave the bound and let deployments flatten.** Rejected — that
   is the current state; the request to extend came from operators
   running into the cap.

## Implementation

1. **This PR.** The ADR lands together with:
   - MOD_A v2.0 → v3.0 (`{0,4}` → `{0,8}`, level table extended,
     boundary rule §2 updated)
   - MOD_H v1.0 → v2.0 (embedded JSON Schema regex + `level.maximum`
     + `parentPath` pattern + `maxDepth.maximum`)
   - Executable canon: `codebook.yaml` `format` block bumped to 8;
     `device-planes.yaml` `arm_tag.value_regex` aligned;
     `codebook.schema.json` `format.max_depth` const + `level.maximum`
     + per-entry pattern updated; the three sibling schemas
     (dynamic-groups, admin-units, policy-targets) updated.
   - Python: `codebook.py`, `governance/drift.py`, `entra_adapter.py`,
     and the two AD-adapter regexes.
   - Markdown regex copies in `MOD_F`, `MOD_I`, `MOD_K`, `MOD_V`.
   - Test fixtures in `tests/test_orgpath_codebook.py` and
     `tests/test_entra_device_orgpath.py` updated to the new bound.
2. **Cross-canon agreement check.** `device_planes.py:_validate_integrity`
   continues to assert `arm_tag.value_regex == codebook.regex` —
   this ADR's invariant is that both move together.
3. **Document registry.** Both MOD_A and MOD_H bumps are recorded
   in `src/uiao/modernization/orgtree/document-registry.yaml` if a
   version field is tracked there (no new IDs allocated).

## Related work

- **ADR-035** introduced the codebook binding and the canonical
  regex this ADR widens.
- **ADR-037** defined the AU naming convention; AU regex is
  unaffected by the depth change because AU naming uses an unbounded
  segment grammar (`^AU-ORG(-[A-Za-z0-9]+)*$`).
- **ADR-038** introduced the device-plane registry and the
  cross-canon agreement check on `arm_tag.value_regex`. This ADR
  is the first widening of the canonical regex since that check
  was instated; the check fires correctly because both sides move
  in this PR.
