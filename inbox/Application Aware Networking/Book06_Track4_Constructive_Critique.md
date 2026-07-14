---
title: "Vol VII Book 06 + Entra Track 4 — Constructive Critique"
subtitle: "An independent peer review of the SaaS-integration-governance document set, written immediately after it — what holds, what a hostile reader breaks first, and what to fix before it leaves draft"
author: "Independent review (Claude Code, at author request)"
date: "2026-07-14 10:03 ET"
---

> **INTERNAL — CONSTRUCTIVE PEER REVIEW · NOT AN ASSESSMENT RESULT**
>
> A constructive critique of the SaaS-integration-governance document set
> produced in a single session on 2026-07-14, prepared at the author's request
> before the work goes to review. It is a peer review meant to strengthen the
> work before a hostile reader (an ISSO, a 3PAO, or a budget committee) sees it
> — **not** a security control assessment, an authorization opinion, or a
> statement of fact about SSA's environment. Every criticism is paired with a
> recommendation; where the set already anticipates a concern, that is noted to
> its credit.
>
> **Caveat on independence:** this reviewer authored the material under review.
> That is a real limitation and the reader should weight it accordingly — a
> self-review reliably misses the assumptions it was built on. The concerns
> below are the ones I could find by attacking my own reasoning; they are not a
> substitute for a reader who does not already believe the thesis.
>
> **Scope reviewed:** `Vol_VII_Book_06_FedAAN_SaaS_Integration_Governance.qmd`
> (+ its `.docx`, `.pptx`, `decks/Vol_VII_Book_06.yaml`, and
> `figs/vol7b06-fig-01-*`), the three `book-sn-saas` closures in
> `aan-compliance-spine.yml`, and `inbox/entra-assessment/04-saas-integration-authorization/`
> (Track 4 README, `Get-EntraSaaSIntegrationInventory.ps1`, and the
> CA-3/SA-9 reconciliation memo). **Scope parameter:** FedRAMP Moderate + GCC
> Moderate only.

## Credit where due

Four things in this set are genuinely right and should survive editing:

- **The no-`UNAUTHORIZED`-verdict design.** The script cannot emit a finding of
  non-authorization, only a review queue. Name-matching gallery display names
  against FedRAMP offering names is permanently unreliable, and the design
  refuses to launder that unreliability into a verdict. The normalization
  deliberately preserves `government` / `federal` / `high` as distinguishing
  tokens. This is the part most likely to be "simplified" by a later
  contributor, and it must not be.
- **The reconciliation narrows rather than widens.** CA-3 and AC-20 are scoped
  down to what they actually cover instead of being stretched over the SaaS
  flow. Widening them would have extended an implemented claim across a flow
  with no evidence — strictly worse than the status quo.
- **SA-9 was not rewritten.** The control already said the right thing and
  named its own evidence. The set treats it as unimplemented rather than
  under-specified, which is the cheaper and more honest diagnosis.
- **Honest Limits is real.** Six limits, including two open questions the set
  cannot answer. It does not pretend the ISA line is derived.

## Bottom line up front

The **diagnosis is sound and now independently corroborated**; the
**prescription is defensible**; the **evidence base is thin in a way the set
does not fully own**.

The single biggest exposure is not a control argument. It is that the entire
set argues for a gate on a population **whose size has never been measured**.
The book, the deck, the memo, and the spine closures all reason about gallery
integrations in an SSA tenant that nobody has enumerated. The first question a
competent ISSO asks is "how many, and how many carry SCIM?" — and the answer
today is "unknown; the script has never been run."

Everything else below is smaller than that.

## Concerns, in priority order

### Concern 1 — The argument rests on an unmeasured population (HIGH)

The set's own sequencing says to run the read-only inventory first. It was not
run. Consequently:

- The book asserts an unguarded act is available; it does not show the act has
  occurred **even once** in this tenant.
- The deck's closing slide says "the size of the problem is currently unknown"
  — which is honest, but it means the preceding sixteen slides argue for a
  process change with no denominator.
- The reconciliation memo recommends taking `SCIM_UNVERIFIED` to the ISSO
  first, without knowing whether that cell contains 0 rows or 40.

A reader can accept every control argument and still decline to act, because
nothing establishes materiality. If the tenant has three gallery integrations
and all three are FedRAMP-authorized, this is a good doctrine chapter and a bad
use of a catalog lane.

> **Recommendation.** Run `Get-EntraSaaSIntegrationInventory.ps1` read-only
> before the book leaves draft, and put the count in the book's opening. One
> real number — "N gallery integrations, M carrying SCIM, K with no marketplace
> match" — converts the whole set from an argument into a finding. If the count
> is small, say so and scale the prescription down; that would be a better
> book, not a weaker one.

### Concern 2 — The 12,940 / zero measurement invites the objection it answers (HIGH)

The headline — 50,172 mentions of SSO, zero of FedRAMP — is rhetorically strong
and analytically weaker than it reads. Microsoft does not put FedRAMP in a
Salesforce SSO tutorial for the same reason a torque-wrench manual does not
discuss vehicle-inspection law. **Measuring that a how-to corpus is not a
compliance corpus proves something nobody disputed.**

The book anticipates this (the "not a criticism of Microsoft's documentation"
callout is good and should stay) — but then leads with the number anyway, and
the deck makes it the closing punchline in red. A hostile reader gets to say
"you measured that a hammer is not a screwdriver," and the callout does not
save the framing because the framing already put the number first.

The number's real payload is narrower and stronger: **an administrator
following the vendor's own guidance end-to-end will never encounter the
authorization question.** That is a claim about the administrator's experience,
not about Microsoft's negligence, and it survives the objection intact.

> **Recommendation.** Reframe the measurement as evidence about the operator
> path, not the vendor corpus. Keep the number; change what it is offered as
> proof of. The figure footer ("Microsoft documents steps 5 and 6 across 12,940
> pages. It documents steps 2 and 4 across zero.") is the version that already
> works — it is about the *steps*, not about Microsoft. Make the prose and the
> deck match the figure, not the other way round.

### Concern 3 — "1,295 tutorials are 1,295 ungoverned SA-9 events" is false as written (HIGH)

A tutorial is not an event. An SA-9 event occurs when someone **integrates** an
application, not when Microsoft **publishes a page**. If the tenant has twelve
gallery integrations, there are twelve SA-9 events and 1,283 pages nobody read.

This is a good slogan and a bad claim. A reviewer who catches it once will
distrust the counting elsewhere — and the counting is otherwise the set's
strongest asset.

> **Recommendation.** "1,295 tutorials are 1,295 **available paths to** an
> ungoverned SA-9 event." Precision costs nothing here and the line keeps its
> force.
>
> **RESOLVED 2026-07-14 10:03 ET.** Fixed in the book (both occurrences) and
> the deck. *Correction to this concern as first written:* it claimed the line
> also appeared in the `book-sn-saas` comment block of
> `aan-compliance-spine.yml`. It does not — the spine says "1,295 tutorials"
> (a true count) and "a catalog of SA-9 events" (i.e. available ones), both of
> which are fine. The third occurrence was a second one in the book. The
> reviewer made the same class of error the concern is about: asserting a count
> of occurrences without grepping for them.

### Concern 4 — The Track 4 script has never executed and carries two unverified constants (HIGH)

It parses, and its name-matching logic was unit-exercised against a synthetic
index. Nothing else about it has been verified:

- **`$CustomAppTemplateId = '8adf8e6e-67b2-4cf2-a259-e3dc5476c621'`** was
  asserted from memory. Its comment honestly says "verify against
  `GET /applicationTemplates` if gallery counts look wrong" — but that is a
  caveat, not a check. If this GUID were wrong, the gallery filter would be
  wrong, and the inventory wrong in a way that looks plausible.
  **RESOLVED 2026-07-14 10:03 ET — verified correct.** The Graph
  `applicationTemplate` reference states it verbatim: *"The application template
  with ID `8adf8e6e-67b2-4cf2-a259-e3dc5476c621` can be used to add a
  non-gallery app."* The same page also confirms the script's
  `preferredSingleSignOnMode` handling (`oidc`, `password`, `saml`,
  `notSupported`) and that `sync` is the only provisioning type. The comment in
  the script should be updated from "verify if counts look wrong" to a citation.
- **The `-Property` list uses PascalCase** (`ApplicationTemplateId`,
  `PreferredSingleSignOnMode`). Track 3 does the same and presumably works, but
  "presumably" is doing load-bearing work for a script whose output is proposed
  as **SA-9 evidence**.
- There are no tests. Track 3 has none either, so this is consistent with the
  suite — but the suite's other scripts are not offered as control evidence.

> **Recommendation.** Verify the template GUID against `GET /applicationTemplates`
> and the property casing against one live call before the artifacts are cited
> as evidence for anything. Both are minutes of work. Until then the README
> should say the script is unexecuted — it currently reads as ready.

### Concern 5 — The set claims a closure the control library says is not implemented (MED)

`aan-compliance-spine.yml` now closes SA-9 for `book-sn-saas`, with a necessity
anchor. UIAO's control library carries `sa/SA-9.yml` at
`status: not-implemented`. Both statements are simultaneously true — the spine
closure is an architectural claim about a mechanism the book specifies; the
library status is an implementation state — but the set never says so, and a
reader who knows both corpora will read them as contradictory.

This is aggravated by the AAN↔UIAO doctrine: AAN is supposed to stand alone,
so the book cannot resolve the tension by pointing at UIAO's library.

> **Recommendation.** One sentence in the book's Closure Necessity making
> explicit that spine closures describe the mechanism the book specifies, not a
> deployed state. This is probably true of every closure in the spine and may
> deserve stating once in Vol 0 rather than here.

### Concern 6 — The ISA line is asserted, and CA-3's spine closure encodes the assertion (MED)

To its credit the book records this in Honest Limits as an open question. But
it is not merely an open question — **it is already encoded as a control
closure.** `CA-3` in the spine states SCIM-provisioned integrations require an
ISA and SSO-only ones do not, and `RequiresIsaUnderCa3 = HasScimProvisioning`
in the script operationalizes it. Password-SSO stores credentials in Entra and
replays them, which is arguably a standing flow of secrets.

An open question in prose is fine. An open question compiled into a control
closure and a data column is a decision that has been made without being made.

> **Recommendation.** Decide it before the book leaves draft, or mark the CA-3
> closure provisional in the spine. Do not ship a control closure whose
> governing rule the same document calls "a judgement, not a derivation."

### Concern 7 — KSI-SCR is a first use, and nothing validates KSI values (MED)

`book-sn-saas` introduces `KSI-SCR` to the AAN spine, which previously used only
CMT / CNA / IAM / MLA / PIY / SVC. KSI-SCR is valid in the CR26 catalog
(Supply Chain Risk, `KSI-SCR-MIT` / `KSI-SCR-MON`), so the choice is defensible
— but `render_authorities_table.validate()` checks books, gates, slots, drivers
and planes, and **does not check `ksi` at all**. A wrong KSI would render into
the authorities table and the generated docx silently. (This reviewer's first
instinct was `KSI-TPR`, the FedRAMP 20x name, which does not exist in the
catalog — the guard rail that caught it was manual.)

> **Recommendation.** Add KSI-vocabulary validation to `validate()`, sourced
> from `fedramp_cr26_catalog/mappings/ksi-mapping.yaml`. Cheap, and it closes
> the same class of hole that the control-library `status` field had open until
> PR #1174.

### Concern 8 — The reconciliation memo's central caveat is now known to be unactionable (MED)

The memo tells the reader: *"`ac/AC-20(1).yml` does not exist… **but**
`index.yaml` declares the library a deliberate 247-of-323 curation, with the
SSP (UIAO_185 §3) carrying the remainder at summary level. Check the SSP before
calling this missing."*

That check has since been performed and the caveat does not survive:
`UIAO_185` is a **96-line template**; its §3 is an **18-row family-level
table** whose counts sum to **249**, not 323; it contains **zero** control
identifiers and zero mentions of `AC-2(1)`, `AC-20(1)`, or `SA-9`. The
76-control delta is not carried there or anywhere else.

So AC-2(1) — the single most on-point control for SCIM provisioning, and in the
Moderate baseline — is genuinely unmapped, as is AC-20(1). The memo currently
sends the reader to a document that cannot answer the question.

> **Recommendation.** Correct the memo: state that AC-20(1)/AC-2(1) are real
> gaps, not curation. Separately, `index.yaml`'s claim that the SSP carries the
> all-323 mapping is false and should be fixed at source — it is load-bearing
> for anyone reasoning about library coverage, and it silently converted two
> real gaps into "probably fine" for the duration of this session.

## Cross-cutting, lower-severity notes

- **The deck and the book share a single Date Code (2026-07-14 09:08 ET), but
  the book has since been edited** (the independent-corroboration section). Per
  authoring-spec §1 the code should have been bumped and the derivatives
  re-rendered. The `.docx`, `.pptx`, and the distribution kit are now behind the
  `.qmd`. **Fix:** bump, re-render, rebuild.
- **The distribution kit was built from a tree four commits behind `main`** and
  is missing `Vol_0_Book_00`, `Vol_0_Book_00a`, `Vol_0_Book_02`, and
  `authorities-book-04.md` changes. It should not be distributed as-is.
- **`figs/vol7b06-fig-01` carries no Date Code**, so it cannot lag the book —
  correct per BUILD-DERIVATIVES, and worth keeping as the pattern.
- **The AAN Vol VII figures use a palette variant** (`#1F3A5F` / `#1A9E8F` /
  `#D4860B`) that differs from canonical `svg-style/palette.json`
  (`#0D1B2E` / `#1E8C8C` / `#D4A017`). Book 06's figure correctly matches its
  Vol VII siblings, but the two palettes are diverging silently and neither
  file references the other.
- **`render_svg_images.py` cannot see `inbox/`** (`SCAN_ROOTS` is `docs/` +
  `src/uiao/canon/`), so AAN figures require an explicit path. A bare run
  silently renders nothing for this book while rewriting 22 artifacts under
  `docs/`. BUILD-DERIVATIVES implies the script works; it does not say it needs
  the path.
- **The external corroborating assessment is unattributed.** The book quotes it
  as "a separate NIST SP 800-53 assessment… written without reference to this
  book," which is accurate but unciteable. Its provenance is unknown and two of
  its seven sources are SEO/marketing sites. **Fix:** either attribute it
  properly or present the corroboration as an observation rather than a source.

## Prioritized actions

1. **Run the inventory.** Put a real count in the book. (Concern 1 — everything
   else is cosmetic next to this.)
2. **Fix the "1,295 events" line in all three places.** (Concern 3 — minutes.)
3. **Verify the template GUID and the `-Property` casing.** (Concern 4 —
   minutes, and the script is otherwise offered as evidence.)
4. **Reframe the 12,940 measurement around the operator path.** (Concern 2.)
5. **Decide the password-SSO / ISA question, or mark CA-3 provisional.**
   (Concern 6.)
6. **Correct the memo's SSP caveat and fix `index.yaml`'s false claim.**
   (Concern 8 — the `index.yaml` half affects everyone, not just this set.)
7. **Add KSI validation to `validate()`.** (Concern 7.)
8. **Bump the Date Code, re-render, rebuild the kit from current `main`.**

## Closing

The set's thesis survives this review: the authorization question is absent
from the vendor path, absent from this series before Book 06, absent from the
UIAO control library's implemented state, and — per the independent assessment
— absent from at least one other reader's analysis of the same corpus. Four
independent absences is a finding.

What the set has not earned yet is **materiality**. It argues, correctly, that
a gate is missing. It has not shown that anything walked through the gap. Those
are different claims, and only the second one moves a budget.

Run the inventory.
