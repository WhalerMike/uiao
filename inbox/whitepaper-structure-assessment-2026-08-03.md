# Whitepaper Structure Assessment — 2026-08-03

Structural (not content-fidelity) review of all 22 papers under
`docs/customer-documents/whitepapers/`, scoped to the question: *does
each paper have the load-bearing sections a whitepaper needs to move a
reader from "informed" to "acting" — problem statement, executive
summary, evidence, honest limits, conclusion, call to action?* This is
a companion to `inbox/whitepaper-content-assessment-2026-07-26.md`
(which covers factual/canon drift) — that memo is not re-litigated
here.

## Answer to "should they all have a call to action?"

**Yes, and today almost none do.** Of 22 papers, exactly **one**
(`federal-application-aware-networking-architecture.qmd`) closes with
a labeled `## Call to Action` section plus a concrete "six steps to
start this quarter" list — added in PR #1400, so the pattern already
exists in the corpus. Two more
(`zero-trust-governance-whitepaper.qmd` §8,
`zero-trust-governance-principles.qmd` §13, both "What an agency can
do this quarter") get most of the way there but aren't labeled as a
CTA and stop short of naming an engagement mechanism (assessment,
pilot, contact). The remaining **19 papers end on a Conclusion,
Provenance/References block, or — in a few cases — an appendix**, with
no explicit next step for the reader. For externally-releasable,
ATO-package-ready documents whose stated purpose (per `index.qmd`) is
to move a federal CIO/CISO/assessor audience toward a decision, that's
a real gap: every paper argues a case and then hands the reader
nothing to do with the conclusion.

## Answer to "should they all have a problem statement?"

**Yes, and most already do — just not uniformly labeled.** Only one
paper (`aodim-executive-whitepaper.qmd`) has a literal `# Problem
Statement` header, but 13 of 22 have a *functional* equivalent early
in the document (`## The Core Problem`, `## The federal SSOT problem`,
`## Split-Brain DNS: The Structural Problem`, `## The False Versus`,
"the one sentence this turns on," etc.) — a clear pain/tension framing
in the first third of the paper. The gap is a smaller group of **6
papers that open with description or mechanics instead of a
problem**: `git-server-interfaces-whitepaper.qmd` (opens with
"architectural context"), `orgpath-composability-matrix.qmd` (opens
with a positioning claim), `scubagear-integration-whitepaper.qmd`
(opens with adapter registration mechanics),
`snowflake-keypair-vs-uiao-orgpath.qmd` (opens with a scope
disclaimer), `zta-scuba-relationship.qmd` (opens as a tool-comparison
rather than a pain point), and `federal-hrit-productization.qmd`
(opens with a mandate landscape survey rather than a stated problem).
These are functional, well-cited papers — they just ask the reader to
infer why they should keep reading instead of telling them.

## What else a good whitepaper should have (and what this corpus does well)

Standard whitepaper craft, mapped to what's actually present here:

| Element | Why it matters | Corpus coverage |
|---|---|---|
| Problem statement (named, early) | Gives the reader a reason to keep reading | 13/22 explicit, 6/22 implicit-only, 3/22 comparison-framed |
| Executive summary | Lets a time-constrained exec get the argument in 30 seconds | 14/22 (8 "narrative"-genre papers use a lighter "In this whitepaper/narrative" framing instead — see below) |
| Evidence / citations | Credibility — claims trace to something | Strong overall: most papers cite ADRs, canon docs, or external standards inline; ~9 papers lack a dedicated References/Sources/Provenance section even where inline citation exists |
| Honest limits / "what this is not" | Rare and valuable — pre-empts the skeptical-assessor pushback | 8/22 have a dedicated section (`bod-25-01`, `modernization-governance`, `scubagear-integration`, `ticket-to-machine`, `uiao-governance-os` "What this is not", `zero-trust-governance-*` ×2, partial in a few more). **This is a genuine corpus strength — recommend making it standard, not optional.** |
| Conclusion | Closes the loop back to the problem statement | 12/22 have a labeled Conclusion/"Bottom line"/"Closing position" |
| Call to action / next steps | Converts argument into reader action | 1/22 labeled, 2/22 CTA-adjacent, 19/22 absent |
| Status/freshness metadata | Tells the reader how much to trust point-in-time claims | Handled well at the *index* level (Active/Draft/Aspirational badges in `index.qmd`); not always echoed in-document |

### A structural note: two genres, one missing a closer

The corpus splits cleanly into two families:

1. **Policy/architecture papers** (numbered sections, `### Executive
   summary` → `### N. Topic` → `### Honest limits` → `### Conclusion`)
   — `uiao-governance-os-whitepaper`, `zero-trust-governance-*` (both),
   `modernization-governance-whitepaper`, `scubagear-integration-whitepaper`,
   `bod-25-01-close-before-assess`, `federal-hrit-productization`,
   `federal-ssot-alignment`, `ticket-to-machine-not-ticket-to-human`,
   `uiao-vs-native-tools`. This family is closest to "done" — it
   already has the Honest-Limits/Conclusion skeleton; it mainly needs
   a CTA appended after Conclusion.
2. **Narrative papers** ("In this whitepaper/narrative," "the one
   sentence this turns on," Act/Part structure) —
   `modernization-journey`, `hybrid-join-without-governance`,
   `infoblox-hybrid-dns-unified-ddi`, `tic3-sdwan-vs-dia`,
   `federal-application-aware-networking-architecture`,
   `snowflake-keypair-vs-uiao-orgpath`. This family deliberately
   substitutes the exec-summary/conclusion bookends for a narrative
   arc, which is a legitimate stylistic choice — but it means these
   papers currently end on a "how this maps to canon" or
   Provenance/Sources block rather than a resolution. AAN
   (`federal-application-aware-networking-architecture`) already
   proved the pattern of closing a narrative paper with a Call to
   Action; it's the template to replicate across the other five.

`aodim-executive-whitepaper.qmd` and `ad-to-entraid-migration-problem.qmd`
sit outside both families — they're the oldest docx-imports in the
set (also flagged in the 2026-07-26 content memo for canon drift) and
have the thinnest structure of the 22: no Honest Limits, no CTA, and
(for `aodim-executive-whitepaper`) no citations at all.

## Recommendation

Don't rewrite all 22 at once. Suggested sequencing:

1. **Add a `## Call to Action` closer to the 9 "policy/architecture"
   papers first** — they already have a Conclusion to hang it off of;
   this is close to a mechanical addition (2–4 bullets: request an
   assessment, pilot scope, point of contact/next artifact to read).
2. **Port the AAN CTA pattern to the 5 remaining narrative papers**
   once the policy-paper pass validates the wording/tone.
3. **Standardize "Honest limits" as a required section** template-wide
   — it's currently the corpus's best differentiator and only present
   in a third of papers.
4. **Add an explicit problem-statement header** to the 6 papers that
   currently open with mechanics/description
   (`git-server-interfaces-whitepaper`, `orgpath-composability-matrix`,
   `scubagear-integration-whitepaper`, `snowflake-keypair-vs-uiao-orgpath`,
   `zta-scuba-relationship`, `federal-hrit-productization`) — likely a
   short (2–4 sentence) insert before their existing opening section,
   not a rewrite.
5. **`aodim-executive-whitepaper.qmd` and
   `ad-to-entraid-migration-problem.qmd`** need the most work of the
   22 — combine this structural pass with the canon-drift fixes
   already queued for them in the 2026-07-26 content memo (Tier 2,
   items 1 and 8) rather than touching them twice.

This memo is assessment only — no whitepaper content changed. Tier 2
items above are candidates for follow-up PRs, one genre-slice at a
time so each is independently reviewable (same rationale the 2026-07-26
memo used for content fixes).
