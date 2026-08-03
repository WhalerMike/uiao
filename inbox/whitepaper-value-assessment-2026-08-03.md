# Whitepaper Value Assessment — 2026-08-03

Content-quality review of all 22 papers under
`docs/customer-documents/whitepapers/` — not another structural
checklist (see `inbox/whitepaper-structure-assessment-2026-08-03.md`
for exec-summary/CTA/conclusion presence) and not a canon-drift audit
(see `inbox/whitepaper-content-assessment-2026-07-26.md` for factual
staleness). This memo asks a different question per paper: **does the
argument earn its length, is the evidence real or asserted, and would
a skeptical reader in the stated audience come away persuaded?**

Seven parallel reviewers each read a track's papers in full and scored
them independently; this memo synthesizes their findings. Where a
prior content-drift flag turned out to already be fixed or overstated,
the reviewer says so explicitly below rather than re-flagging it.

## Corpus-wide patterns (cross-cutting, not paper-specific)

1. **Composite narratives don't always disclose they're composites.**
   `modernization-journey.qmd` and
   `federal-application-aware-networking-architecture.qmd` both run a
   specific, named-detail agency scenario (twelve regions, a named
   employee, named field offices) for hundreds of lines before a
   closing Provenance note — or nothing at all, in AAN's case —
   reveals it's synthetic. `infoblox-hybrid-dns-unified-ddi.qmd`, by
   contrast, discloses synthesis vs. sourcing up front and mid-document
   every time it happens. The honest-disclosure pattern already exists
   in the corpus; it's just not applied consistently.
2. **Sibling papers duplicate their weaker argument, not just their
   content.** `zero-trust-governance-whitepaper.qmd`'s framing
   sections restate `zero-trust-governance-principles.qmd`'s thesis
   with the evidence stripped out (no CVEs, no incidents) — a reader
   hits the thinner version, not just a shorter one, if they read
   whitepaper first. Similarly `modernization-journey.qmd`'s Act 4 and
   `hybrid-join-without-governance.qmd`'s governed path both narrate
   the same L0–L4 ladder; hybrid-join's version is more concrete.
3. **Load-bearing numbers are frequently self-authored.** The 47%/53%
   SCuBA/ZTA overlap split, the 10-of-29 BOD-25-01 KSI ratio, and the
   22–30%/85–95% coverage claims in `uiao-vs-native-tools.qmd` are each
   computed from a single internal source or non-representative sample
   and then presented with declarative confidence in an executive
   summary. Several papers (zta-scuba, bod-25-01) do caveat this
   honestly in the body — the problem is the caveat doesn't travel with
   the number when it's repeated up top.
4. **Status/lifecycle metadata occasionally contradicts the paper's
   own body.** `federal-hrit-productization.qmd` claims `Active` while
   its own conclusion calls its primary canon source "Draft, still
   under refinement." `git-server-interfaces-whitepaper.qmd` claims
   `adopted`/Tier 1 while §5.3/§9.2 concede its central mechanism is
   "still under operational validation." `infoblox-hybrid-dns-unified-ddi.qmd`
   just had its own `version` frontmatter bumped to 0.4 while its
   in-body "Document status" callout still says "DRAFT v0.3" (a
   same-day inconsistency introduced by this week's CTA-addition PR —
   worth a one-line fix).
5. **The papers with the most explicit self-limitation are the
   strongest, not the weakest.** `hybrid-join-without-governance.qmd`
   (§4, "what hybrid join still doesn't satisfy"),
   `zero-trust-governance-principles.qmd` (§14 Honest Limits),
   `ticket-to-machine-not-ticket-to-human.qmd` (disclosing a real
   command-injection finding in its own reference implementation), and
   `federal-ai-governance-submission-readiness.qmd` ("where an
   evaluator will find gaps") all rank High precisely because they
   argue against themselves before a skeptical reader can. This is a
   real, replicable corpus strength — worth calling out to whoever owns
   these papers as the house style to standardize on, not just a nice
   accident in four documents.
6. **A few papers are structurally over-scoped for their own billing.**
   `ticket-to-machine-not-ticket-to-human.qmd`'s frontmatter promises a
   single paper "so readers don't have to read four books," then grows
   a code security review, an access-governance extension, and a
   vendor market analysis inside itself — becoming longer than what it
   claims to replace. `infoblox-hybrid-dns-unified-ddi.qmd` similarly
   carries ~1,100 lines of DNS-record reference material before its
   real decision content (Part 8–10) arrives.

## Per-paper assessments

### Track 1 — Governance Foundations

#### uiao-governance-os-whitepaper.qmd — **Medium-High**
- Value: the flagship's real spine is §3's shipped/partial/target
  maturity table (falsifiable, not promotional) and §8's honest "what
  this is not."
- Weakness: §4 ("why 'operating system,' not 'framework'") is
  argument-by-metaphor that never cashes out into a reader decision;
  heavy citation-as-assertion elsewhere (e.g. "canon names this posture
  Active Governance" is declared, not argued).
- Recommendation: cut §4, replace with one worked example tracing a
  single control's evidence bundle end-to-end (telemetry → claim →
  bundle → OSCAL) — currently described only in the abstract, split
  across three sections.

#### zero-trust-governance-whitepaper.qmd — **Medium**
- Value: §2's ZTMM-pillar-to-canon-anchor table and §6's GCC-Moderate
  boundary section are concrete and non-duplicated.
- Weakness: §1/§3 restate `zero-trust-governance-principles.qmd`'s
  thesis without its evidence, and the two papers take different
  positions on the same architectural bet (whitepaper treats
  identity-as-root uncritically; principles explicitly warns it "can
  recreate the failure mode Zero Trust is supposed to retire").
- Recommendation: cut the framing sections to a pointer at
  `zero-trust-governance-principles.qmd`; reinvest length into deepening
  the pillar-mapping table into worked mini-cases — its one truly
  unique contribution.

#### zero-trust-governance-principles.qmd — **High**
- Value: best-evidenced paper in the corpus — Storm-0558, ESXiArgs
  (CVE-2021-21974), CVE-2024-37085, a CSRB "preventable" finding, all
  named with dates. §12's "tools you already have" is unusually
  non-self-serving. §14 Honest Limits has six distinct, specific
  caveats.
- Weakness: at ~780 lines across 15 sections, reiterates its own
  thesis in six different places; §9's most original claim (the
  unification layer becomes the highest-value target) breaks its own
  incident-grounding discipline by asserting with no example.
- Recommendation: split §9–10 (whole-agency unification + SCuBA/ZTA
  case) into a separate shorter paper so a busy executive can finish
  the core argument.

#### modernization-governance-whitepaper.qmd — **Medium**
- Value: §1's five concrete consequences of the OU→attribute inversion
  and §2's three distinct failure-mode arguments are real causal
  arguments, not pattern lists. §7's admission that OU-driven agencies
  "will not realize most of the substrate's value" is a genuinely risky,
  non-hedged claim.
- Weakness: §3 (AODIM) is almost entirely a pointer to a paper that
  already exists standalone; §6 re-runs the governance-os whitepaper's
  evidence-chain argument nearly verbatim; the exec-summary's "most
  architecturally consequential modernization most agencies will
  execute this decade" claim is asserted with no survey or comparison.
- Recommendation: cut §3 to two sentences, use the reclaimed space to
  walk one attribute (e.g. "classification clearance") through all five
  migration phases end to end — currently described procedurally, never
  demonstrated.

### Track 2 — Identity & Directory Modernization

#### ad-to-entraid-migration-problem.qmd — **Medium**
- Value: the AD-governance-concepts→Entra-equivalents table is the
  strongest evidence in the paper; "The Session vs. Telemetry Divide"
  names a genuinely original architectural tension strong enough to be
  its own paper.
- Weakness: three arguments (governance gap, session/telemetry
  mismatch, product positioning) are bundled into one paper and each
  gets diluted; the SSOT/root-namespace idea set is stated fully,
  restated, then restated again by the closing paragraph. (Note: the
  "eight core concepts / lists seven" and leftover second-person-tone
  issues flagged in the prior content memo were not found in the
  current text — appear already fixed.)
- Recommendation: split the session/telemetry argument into its own
  paper; delete the "Core Principles Map" section in favor of a
  one-paragraph pointer.

#### aodim-executive-whitepaper.qmd — **Medium-High** (technical) / lower for its stated Executive audience
- Value: concrete worked examples (`extensionAttribute` mapping,
  dynamic-group rule syntax) are the strongest evidentiary move in the
  corpus — shows the mechanism instead of asserting it. (Note: the
  retired-Model-B and zero-citation issues flagged in the prior content
  memo were not found in the current text — the paper now describes
  Model C and cites six canon documents. Appears already reconciled.)
- Weakness: "Key Benefits" is a bare adjective list with no numbers;
  "Risks and Mitigations" is symmetrically empty (each risk gets a
  mitigation that just restates the pitch); no cost/timeline/headcount
  figure anywhere despite the Executive audience tag.
- Recommendation: add one paragraph of quantified business stakes
  before "Architecture Overview," and rewrite "Key Benefits" as
  before/after deltas instead of adjectives.

#### uiao-vs-native-tools.qmd — **Medium-High** (technical evaluator) / Medium overall
- Value: the "Consume vs. Build" table (§7) is the paper's best
  argument — traceable to the evidence earlier in the document, not
  asserted independently. §9's import-adapters description names module
  paths and function names a reader can verify. (Note: the
  coverage-percentage internal contradiction and "conceptual future
  module" framing flagged in the prior content memo were not found in
  the current text — figures are internally consistent and §9 is
  titled "Implemented." Appear already fixed.)
- Weakness: three overlapping quantification passes over the same
  ground (domain matrix, gap-analysis table, Appendix A) — a reader who
  finishes §3 has already seen most of Appendix A. The headline
  22–30%/85–95% coverage claim is UIAO scoring UIAO against its own
  rubric, labeled "illustrative" but never otherwise addressed as
  circular. §8 "Competitive Messaging" breaks the evidentiary register
  with embedded VC/customer/engineer pitches.
- Recommendation: replace at least one percentage callout with a single
  worked example (an actual or representative assessment run, findings
  counted) so the headline claim is anchored in something reproducible.

#### modernization-journey.qmd — **Medium**
- Value: the closing canon-mapping table's self-corrections ("OrgPath
  is an addressing attribute... not a governance primitive") are a rare,
  valuable honesty signal. Act 2's technical mechanics (F5 proxies, NAT
  breaking Kerberos sessions) are the strongest evidentiary passage.
- Weakness: the composite-agency narrative reads as a real client case
  for ~500 lines before the closing Provenance callout discloses it
  isn't; Act 3 invokes "electoral integrity" with no argument connecting
  a generic modernization narrative to election systems; large Act-4
  passages duplicate `hybrid-join-without-governance.qmd` near-verbatim.
- Recommendation: move the "this is a narrative synthesis" disclosure
  from the closing callout up into the opening one.
- **Track note**: if forced to cut one of this pair, `hybrid-join` is
  the higher-value document for a technical reader — its loss-ledger
  table and ungoverned-path mechanism detail are more concrete than
  modernization-journey's Act 4 prose covering the same doctrine.
  modernization-journey's unique contribution is strictly the
  emotional/narrative arc for buy-in — real, but narrower than its
  length suggests.

#### hybrid-join-without-governance.qmd — **High**
- Value: the most actionable, evidentially disciplined paper in the
  set. The §3 loss-ledger table names exactly what classic AD provided
  and maps each loss to a specific remediation. §4 ("what hybrid join
  still doesn't satisfy") is a rare, valuable self-limiting move.
  Sourcing discipline (Microsoft Learn URLs cleanly separated from
  canon claims) is the cleanest in the track.
- Weakness: asymmetric rigor — the ungoverned path is described with
  exact mechanism specificity, the governed path stays at the level of
  principle with no equivalent operational detail; "effortless is the
  hazard" is restated near-verbatim four times.
- Recommendation: give the governed path the same mechanism-level
  specificity as the ungoverned one — name the actual API/PowerShell
  calls that execute an OrgPath-scoped wave.

#### federal-ssot-alignment.qmd — **Medium**
- Value: §4's GCC-Moderate three-way compliance conflict (TIC 3.0 CASB
  inspection vs. ZTMM posture fidelity vs. FedRAMP 20x boundary
  cleanliness) is genuinely sharp and non-obvious, anchored to a named
  standing finding ID. §5's mandate-to-capability-to-canon table does
  real crosswalk work.
- Weakness: §3.4's "six governance domains" sits one section from
  canon's real "six control planes" (ADR-030) — both exactly six, both
  leading with Identity, rendered in the same visual register. A
  disambiguating footnote exists, but a skimming Executive/Customer
  reader (the stated audience) is likely to conflate them anyway.
  Several claims argue by asserted analogy ("mirrors the federal MDM
  pattern exactly") without showing where the analogy might strain.
- Recommendation: resolve the six-domains/six-control-planes collision
  structurally — rename the taxonomy, or present it explicitly as an
  overlay *on* ADR-030's six planes — rather than relying on a footnote.

### Track 3 — Zero Trust Assessment & Compliance Closure

#### bod-25-01-close-before-assess.qmd — **Medium** (Medium-High for its actual internal-compliance-leadership audience, weak for the assessor audience it's tagged for)
- Value: the §1 obligations table sharply isolates where agencies
  under-invest. §7 Honest Limits does real work — explicitly disclaims
  that its 10/29 KSI figure is internal-only.
- Weakness: that same 10/29 figure is used with declarative force in
  §3 despite being an internal, non-empirical decomposition; no case
  study of the failure mode being warned against; the six-phase sequence
  is "correct" primarily because it's OrgComp's own sequence — the paper
  never argues why an iterative remediate/assess approach is inferior.
- Recommendation: replace or supplement the internal KSI ratio with one
  concrete worked example (a finding that stayed open N months
  scan-only vs. closed under the phased model).

#### scubagear-integration-whitepaper.qmd — **Medium-High** (architects) / Low (its tagged Customer audience)
- Value: the `adapter-registry.yaml` excerpt and five-property
  walkthrough are concrete, falsifiable. §6 ("why interval matters")
  makes a real technical distinction with a worked example.
- Weakness: §5 is a wall of internal PR numbers and cross-references
  that proves connectedness to other docs rather than advancing an
  argument. Strong claims ("a 3PAO can re-run the assembly months later
  and verify the hash") are asserted with no example hash or
  walkthrough.
- Recommendation: move §5's PR catalogue to a footnote; replace with one
  concrete before/after trace of a single real SCuBA finding through
  the full pipeline.

#### zta-scuba-relationship.qmd — **High** relative to its narrow purpose / **Medium** as a standalone whitepaper
- Value: the three-column overlap table is precise and immediately
  usable. "Two caveats that matter more than the percentage" proactively
  undercuts its own headline statistic — an unusually honest move.
- Weakness: despite that caveat, the 47%/53% split (from a single
  non-representative demo tenant) still leads the exec summary with the
  same visual weight as the qualitative caveats, and will get quoted
  without them.
- Recommendation: move the percentages out of the executive summary
  into the caveated table further down.
- **Track note**: this paper is thin relative to the other three — no
  real thesis to defend, no case study — but earns its slot
  functionally: both `bod-25-01` and `scubagear-integration` explicitly
  defer to it rather than re-explaining the ZTA/SCuBA distinction
  inline. Keep it, but consider recategorizing it as reference/FAQ
  material rather than marketing it at the same weight as the other
  three.

#### ticket-to-machine-not-ticket-to-human.qmd — **Medium**
- Value: §11 (External Validation) is the standout — it brings in
  independent research that *corrects* two of the paper's own prior
  assumptions, genuine self-correction rather than retrofitted
  confidence. The §4 disclosure of real vulnerabilities in its own
  reference implementation (`AdHybridClient.js` — command injection,
  cleartext password) is a remarkable level of candor.
- Weakness: fails its own stated purpose — billed as "one paper instead
  of four books," it absorbs a code security review, an
  access-governance extension, a PKI carve-out, and a vendor
  landscape analysis, becoming longer and denser than what it claims to
  replace. `lifecycle: adopted`/Tier 1 sits oddly on a `Draft`-status
  paper with a live "do not run against production" security warning.
- Recommendation: split along its own seams — keep the core Closure
  Necessity argument (§§1-7, 10, 12) as the promised single paper; spin
  the code review, access-governance extension, and vendor analysis out
  into linked appendices.

### Track 4 — Network & Infrastructure Modernization

#### federal-application-aware-networking-architecture.qmd — **High** (CIO/CISO) / **Medium** (architect/engineer)
- Value: the four-act arc anchored by a recurring concrete figure
  ("Jane Smith, four environments") makes an abstract SSOT argument
  memorable. The physics argument (Portland–DC propagation floor,
  LEO vs. GEO, 5G CUPS/MEC) is numerically precise and correctly used
  to puncture the "we bought DIA, we're modernized" fallacy. The Federal
  Framework Alignment table and six-step CTA give assessors and CIOs
  something concrete to act on.
- Weakness: the "your agency" narrative — twelve regions, a named
  employee, named systems — is a synthetic composite per its own
  frontmatter, but nothing in the body discloses that (unlike the
  infoblox paper, which discloses synthesis inline every time). The core
  claims repeat near-verbatim three-plus times. The mainframe token-bridge
  section is bolted on after the five principles conclude rather than
  integrated into Principle 5, which it claims to be part of.
- Recommendation: add an explicit "this is a composite scenario, not a
  documented agency" disclosure near the executive summary, matching
  the honesty standard its sibling papers already hold themselves to.

#### tic3-sdwan-vs-dia.qmd — **High**
- Value: the "honesty clause" discipline is unusually rigorous — it
  proactively names where its own claims are incomplete (e.g., stating
  outright that a Microsoft tenant-restriction requirement is "a hard
  contradiction, not a tradeoff"). Part 6 spends real space arguing
  against the very technology it promotes, citing an appropriately
  hedged CVE. CP-8 is handled at enhancement-level granularity most
  architecture papers skip.
- Weakness: some engineering estimates ("~1.5× fiber-route factor,"
  BFD defaults) are stated with the same declarative confidence as
  cited standards but have no traceable source — the honesty-clause
  standard applied rigorously to compliance claims is applied unevenly
  to the paper's own numbers. No executive on-ramp despite claiming an
  Executive audience.
- Recommendation: add a one-page decision-maker digest before Part 1 so
  the Executive audience tag is actually served.

#### infoblox-hybrid-dns-unified-ddi.qmd — **Medium-High** (reference) / **Medium** (as persuasive whitepaper)
- Value: Part 3's security-integration matrix (19 record types ×
  DNSSEC/PKI/threat-defense relevance) is genuinely rare, bookmarkable
  reference material. The candor is real and unusual — the Document
  Status callout and Appendix B self-report an open citation error that
  was found and corrected. Part 8/10.2 fill a documentation gap neither
  vendor has published, with a concrete five-decision checklist.
- Weakness: Part 7's "the industry's most complete answer" framing is
  vendor-superlative language in a paper claiming vendor-neutral
  synthesis — competing DDI platforms are never named, so the
  superlative is asserted, not argued. The core split-brain mechanic is
  independently re-derived from scratch at least four times. The
  frontmatter now says `version: 0.4` (from this week's CTA-addition
  PR) while the in-body "Document status" callout still says "DRAFT
  v0.3" — a fresh, easy-to-fix inconsistency.
- Recommendation: split Part 3 (record catalog) and Part 7.5 (ecosystem
  integrations) into a reference appendix; lead the remaining argument
  with an executive digest so Part 10.2's five decisions are reachable
  without 1,100 lines of taxonomy first. Fix the v0.3/v0.4 mismatch.
- **Track note**: at ~1,800 lines, the paper's genuine hard-to-find
  value (Part 8's interception analysis, Part 10.2's five decisions)
  occupies a relatively small fraction of the document. Comparably
  dense `tic3-sdwan-vs-dia.qmd` (825 lines) threads decision content
  throughout rather than back-loading it — a materially better
  length-to-decision-value ratio.

#### git-server-interfaces-whitepaper.qmd — **Medium**
- Value: the six-interface-family taxonomy (A–F) turns a sprawling
  technical surface into something auditable; §9.1's NIST crosswalk is
  genuinely assessor-usable. §8's boundary/egress framing is concrete
  and falsifiable.
- Weakness: the frontmatter claims `platform-server-build.qmd@v1.5`
  provenance, but the body repeatedly cites "ADR-041 v1.3" as authority
  for its database-profile claims (ADR-041 itself is still frozen at
  v1.3 — the whitepaper is faithfully citing upstream, but never flags
  that gap to the reader). More seriously: the paper markets itself as
  `adopted`/Tier 1 while its own §5.3/§9.2 concede its central
  governance mechanism (JML propagation timing) is "still under
  operational validation" — an internal contradiction, not just a stale
  pointer.
- Recommendation: either re-baseline the in-body citations against the
  live v1.5 guide or explicitly flag the ADR-041 gap; downgrade
  `tiers_adopted` or annotate the Phase-14 claims with the same
  "still under validation" caveat the body already uses internally.

### Track 5 — Federal Program-Specific Alignment

#### federal-hrit-productization.qmd — **Medium**
- Value: the Pattern A/B/C taxonomy compresses eleven disparate federal
  HR systems into three data-flow shapes, carried consistently through
  every section. The "Program currency" callout proactively flags its
  own staleness relative to a December 2025/June 2026 award — a rare
  self-correcting move.
- Weakness: a `provisioning-source: declared` invariant in the §6
  comparison table sits next to three real, independently-citable
  invariants — checked against canon, it doesn't trace anywhere. In a
  paper whose entire rhetorical premise is "mechanical, not
  aspirational," one ungrounded claim next to three grounded ones is
  disproportionately damaging to the whole citation apparatus.
  `status: Active` also sits oddly next to the paper's own admission
  that its primary canon source is "Draft v0.2, still under
  refinement."
- Recommendation: either register the provisioning-source invariant as
  a real canon artifact or delete it from the comparison table —
  don't let one unbacked claim sit beside three grounded ones.

#### federal-ai-governance-submission-readiness.qmd — **High**
- Value: the self-labeled honesty ledger (Active/Proposed/
  Reserved/Profile-only rows, each with a specific ADR/code-path
  anchor) checks out against the repo — verified the L1 scanner exists
  at the cited path and ADR-117's AWS IaC is correctly framed as
  "landed" rather than a live capability. "Where an evaluator will find
  gaps" proactively names weaknesses before a reader can. (Note: both
  issues flagged in the prior content memo — the Azure-only overclaim
  and the AISystemRecord understatement — are already corrected in the
  current text.)
- Weakness: the coverage ledger and the gap-analysis prose section
  substantially duplicate each other. The competitive-differentiation
  claim ("most competitors treat the inventory as a reporting
  spreadsheet") is the one unsourced assertion in an otherwise
  evidence-disciplined document.
- Recommendation: fold the gap-analysis prose into the ledger table as
  a fourth column; back the competitive claim with at least one named
  point of comparison.

### Track 6 — Positioning, Comparison & Vendor Reads

#### orgpath-composability-matrix.qmd — **Medium**
- Value: "How to read the maturity honestly" is a genuine candor
  moment — it states outright that the deployed surface is narrower
  than the designed surface and commits to labeling every cell. The
  three separability facts are concrete, falsifiable claims.
- Weakness: the central "genuine composability" thesis is asserted
  against evidence that mostly contradicts it — of 9 rows in Axis 1,
  only 1 (Microsoft Entra) is Active. "Three worked stacks" presents two
  unbuilt transports as parallel, buyable options alongside the one real
  one — roadmap dressed as menu. The only support for the composability
  claim is the architecture's own ADR quoted at itself, no field
  evidence.
- Recommendation: attach real deployment evidence (tenant count, scale,
  time-in-production) to the one Active row, plus a stated
  promotion timeline for moving a Proposed row to Active.

#### snowflake-keypair-vs-uiao-orgpath.qmd — **Low** relative to its full-whitepaper billing
- Value: the Snowflake-fact sourcing is unusually strong and externally
  checkable (dated MFA rollout phases, the exact WIF GA date). The
  Call to Action's three manual steps are the one part of the paper
  with unconditional standalone value — executable today, no product
  required.
- Weakness: the paper applies the full whitepaper apparatus (five
  numbered "Moves," a five-row typed drift table, a worked four-step
  sequence, a dedicated placement section) to a scenario its own text
  calls "a placement sketch, not an authorization to build" — the
  hedging protects against overclaiming in prose but the
  implementation-level detail overclaims in substance for a reader who
  doesn't reach the disclaimers. The load-bearing premise ("the logic
  is platform-agnostic because the object classes are the same
  everywhere") is asserted in one sentence, never defended.
- Recommendation: cut the implementation-level apparatus down to a
  compressed summary, and lead with — rather than bury — the CTA's
  three manual, adapter-independent steps. Repositions the piece
  honestly as an applied-doctrine brief sized to its actual
  pre-authorization stakes.

## Value tier summary

| Tier | Papers |
|---|---|
| **High** | `hybrid-join-without-governance`, `zero-trust-governance-principles`, `tic3-sdwan-vs-dia`, `federal-ai-governance-submission-readiness` |
| **Medium-High** | `uiao-governance-os-whitepaper`, `aodim-executive-whitepaper` (technical), `uiao-vs-native-tools` (technical), `scubagear-integration-whitepaper` (architects), `zta-scuba-relationship` (narrow purpose), `federal-application-aware-networking-architecture` (CIO/CISO), `infoblox-hybrid-dns-unified-ddi` (reference) |
| **Medium** | `zero-trust-governance-whitepaper`, `modernization-governance-whitepaper`, `ad-to-entraid-migration-problem`, `modernization-journey`, `federal-ssot-alignment`, `bod-25-01-close-before-assess`, `ticket-to-machine-not-ticket-to-human`, `git-server-interfaces-whitepaper`, `federal-hrit-productization`, `orgpath-composability-matrix` |
| **Low** | `snowflake-keypair-vs-uiao-orgpath` |

No paper scored uniformly Low across every dimension — even the
lowest-tier paper (Snowflake) has a genuinely valuable, narrower core
(the CTA's three manual steps, the sourcing) buried inside
over-built apparatus. The corpus's most common failure mode isn't
weak content, it's **scope creep past what the paper's own stated
purpose or audience needs** — narrative papers that don't disclose
they're composite, comparison papers that repeat their own numbers in
three formats, and reference-heavy papers that bury their decision
content under taxonomy. The fix pattern is nearly always the same:
cut/relocate the reference or restated material, and lead with what
the paper's stated audience actually needs to act.
