---
title: "Draft Call to Action sections — AAN-style narrative whitepapers"
status: DRAFT
date: 2026-08-03
depends_on: inbox/whitepaper-structure-assessment-2026-08-03.md (Recommendation #2)
template: federal-application-aware-networking-architecture.qmd's `## Call to Action` (PR #1400)
---

# Draft Call to Action sections

Five of the six "narrative-genre" whitepapers identified in the
2026-08-03 structure assessment lack a Call to Action; the sixth
(`federal-application-aware-networking-architecture.qmd`) already has
one and is the template these are ported from — same shape (intro
paragraph → `::: {.callout-important}` numbered list → closing
paragraph), each tailored to its own paper's content, audience, and
honesty posture. **Nothing has been applied to the whitepapers yet —
these are drafts for review.** Each block below is written to be
pasted in as the final section of its target file, in Quarto/Pandoc
markdown matching the surrounding document's syntax.

---

## 1. `modernization-journey.qmd`

**Insertion point:** after the existing `Provenance` callout (currently the
last block in the file).

```markdown
---

## Call to Action

This narrative describes an arc most agencies are already living
through, whether or not they have named it. The four acts are
diagnostic before they are prescriptive — knowing where an agency sits
on the arc determines what to do next.

::: {.callout-important}
## Five steps to start this quarter

1. **Place your agency on the arc.** Read Acts 1–3 as a diagnostic,
   not history: how many regional AD domains, DCs, and hairpin points
   still exist; how many Act 2 security-layer accretions sit on top of
   them without ever being consolidated. Most agencies find they are
   further into Act 3 — the breaking point — than their own
   architecture diagrams show.
2. **Separate truth from enforcement before you separate anything
   else.** ADR-092's core move — one canonical source of truth with
   providers as governed data planes — doesn't require replacing AD or
   any vendor product on day one. It requires deciding what the
   canonical source is and starting to reconcile providers against it.
3. **Give every object an OrgPath before you give it a new home.**
   Addressing derives from OrgPath, not from which regional AD forest
   an object happens to live in. This is the cheapest, least
   reversible-risk step in the whole arc, and every later step depends
   on it.
4. **Start at L1 Observe, not L3 Enforce.** Active Governance's ladder
   (ADR-092 §3–4) is designed to be entered at the bottom. Report-only
   reconciliation against canon surfaces drift before anything is asked
   to act on it — the same discipline the companion
   [*Flipping 50,000 Devices to Hybrid Join*](hybrid-join-without-governance.qmd)
   paper works through for one concrete operation.
5. **Name an owner for control-plane/data-plane separation,
   application-aware transport, and identity.** These are three
   different engineering disciplines with three different natural
   owners — data governance, network engineering, identity engineering.
   None of them moves if this narrative stays a slide deck instead of a
   plan with names on it.
:::

None of this requires a platform decision or a rip-and-replace
commitment. It requires knowing which act your agency is in, and
starting the reconciliation loop before the next breaking point forces
it.
```

---

## 2. `hybrid-join-without-governance.qmd`

**Insertion point:** after `## Sources` (currently the last section).

```markdown
---

## Call to Action

The two paths in §6 reach the same technical end state. The only
question this paper actually poses is which one your agency is already
on — and whether anyone decided that on purpose.

::: {.callout-important}
## Four steps before the next tenant switch

1. **Check whether the ungoverned path is already live.** Confirm
   whether hybrid-join auto-registration (SCP + GPO) is enabled in your
   tenant today, and if so, since when. A control that "shipped itself"
   the moment the settings were flipped is drift, not policy — it needs
   to be found before it can be governed.
2. **Inventory before you enforce.** Run the ungoverned fleet against
   the loss ledger in §3 — count the duplicate objects, the
   unattributable device-state changes, the non-Windows/BYOD devices
   Conditional Access can't see. This inventory is the input to every
   later wave, not a formality.
3. **Enter at L1 Observe, report-only, before any CA policy can lock
   out the fleet.** The governed path in §5 exists precisely so
   enforcement never runs ahead of coverage data. Skipping straight to
   L3 is how a well-intentioned rollout becomes an outage.
4. **Assign the wave owner.** Someone needs to own the OrgPath-scoped
   wave plan, the AO sign-off on each L3-gated class, and the rollback
   path. If no one owns it, the tenant setting is the plan — which is
   the failure mode this paper describes.
:::

This is a single control, not a program — which is exactly why it's
worth getting right before the next 50,000-device decision arrives on a
shorter deadline.
```

---

## 3. `infoblox-hybrid-dns-unified-ddi.qmd`

**Insertion point:** after the `Document status` callout (currently the
last block).

```markdown
---

## Call to Action

Part 10.2's five configuration decisions are where most of this
paper's risk concentrates — get the redirect-dns destination and
forwarding order wrong, and the rest of the reference architecture
doesn't matter.

::: {.callout-important}
## Five steps before the next SD-WAN or Universal DDI change

1. **Audit the current redirect-dns destination at every branch.**
   Decision 1 (§10.2) is the single most common configuration error —
   any target other than the local BloxOne Endpoint bypasses Universal
   DDI policy entirely, silently.
2. **Verify the forwarding chain order, not just its presence.**
   Umbrella, if used, must sit downstream of BloxOne DDI (Decision 2).
   Confirm this in the running config, not the design document.
3. **Inventory AD DNS records before touching a domain controller.**
   Decision 4 is irreversible to skip — SRV records and
   conditional-forwarding rules cannot be recovered from a
   decommissioned DC. This inventory has to happen *before*
   decommissioning, not during.
4. **Check the sovereign-cloud boundary before promising INR
   telemetry.** If any part of the estate is GCC/DoD, Cisco's INR loop
   (Part 9) is unavailable regardless of SD-WAN version — confirm this
   with the program office before it's designed into a briefing.
5. **Take Appendix B's open questions to the vendors, not around
   them.** Three of six are still open as of this draft. Engaging
   Infoblox and Cisco directly on transparent-proxy mode, per-CSP
   forwarding coverage, and the INR sovereign-cloud roadmap is faster
   than working around unconfirmed behavior.
:::

This paper is still Draft — that describes what's verified, not a
reason to wait. The five decisions above are actionable today
regardless of which Appendix B questions remain open.
```

---

## 4. `tic3-sdwan-vs-dia.qmd`

**Insertion point:** after `## References` (currently the last
section). Note this paper already has a strong ordered checklist
(Part 8 — The Decision Sequence); this CTA is deliberately short and
points back to it rather than re-deriving it, adding only the
calendar/ownership framing Part 8 doesn't cover.

```markdown
---

## Call to Action

Part 8 already compresses this paper to an ordered checklist. What's
still missing from most modernization schedules is a date and an owner
for each of its five steps.

::: {.callout-important}
## Before the next transport or SD-WAN procurement decision

1. **Run Part 8 as a checklist against your current portfolio, not a
   future one.** For every circuit in flight today, answer step 1
   (measured physics within the acquisition envelope) and step 2 (is
   the governor deployed before the pipe carries production traffic) —
   in that order.
2. **File the CA-6 authorization boundary update before cutover, not
   after.** Step 3 is the step most schedules skip. Distributed egress
   is a significant change; the SSP and security-impact-analysis
   paperwork belongs before branches move off the TIC hairpin.
3. **Name the owner for each of the five steps.** Acquisition owns step
   1's SCRM/Section 889 envelope and the CP-8 enhancements; network
   engineering owns steps 2 and 4; the AO/ISSO owns step 3's
   authorization decision; the OrgComp volumes (step 5) are the
   register, not a substitute for an owner.
4. **Bring the physics argument to the acquisition conversation, not
   just the network diagram.** Part 8's one-sentence version — physics
   buys the pipe, diversity buys CP-8, the governor buys the protection
   controls, TIC 3.0 is why you can't stop at the pipe — is written to
   be handed to whoever signs the transport contract.
:::

No future transport class, 6G included, changes which of these four
steps is optional. None of them are.
```

---

## 5. `snowflake-keypair-vs-uiao-orgpath.qmd`

**Insertion point:** after `## Sources (Snowflake product facts)`
(currently the last section). This paper is explicitly framed as
*"a placement sketch, not an authorization to build"* and carries a
`## What this document does not claim` section — the CTA below is
written to stay inside that same honesty posture: it points to what a
reader can do **without** a shipped adapter, and treats the boundary
decision as a conversation to start, not a foregone conclusion.

```markdown
---

## Call to Action

This paper is a reading, not a roadmap — nothing here is blocked on
UIAO shipping a Snowflake adapter. The four-step discipline in the
walkthrough can be applied by hand today; only its *automation*
depends on the boundary decision below.

::: {.callout-important}
## Three steps that don't require a new adapter

1. **Classify every Snowflake principal today, manually.**
   `DESCRIBE USER` and the account-level login-history views answer the
   `password` / `keypair` / `federated` classification Part 2 would
   otherwise automate — the same inventory step the platform-analogous
   SQL Server transformation (`ADR-091`) starts with.
2. **Treat a stored key pair as the bridge it is, not the
   destination.** Rotate on a defined cadence and track rotation as a
   compliance signal now, even without a drift engine watching it —
   key-pair auth is correct and replay-resistant, but `ADR-004`'s
   credential-free destination is still the target.
3. **Answer the boundary question before the automation question.** If
   Snowflake is in scope for a GCC-Moderate deployment, the first real
   decision is not "build the adapter" — it's the gating-ADR
   conversation (`ADR-059`/`ADR-033` pattern) that would classify it
   under a `gcc-boundary` value, or under `commercial-general`
   (`ADR-129`) for a non-federal engagement. That conversation can start
   independently of any engineering work.
:::

If and when that boundary decision authorizes it, the adapter shape in
Part 2 and the OrgPath-rendered access model in Part 3 are already
worked out — this document is the design sketch waiting on that
decision, not a blocker to today's manual discipline.
```

---

## Notes for whoever applies these

- All five keep the AAN template's shape but vary length (3–5 steps)
  and register to match each paper's own voice — the Snowflake one in
  particular is deliberately softer than the others because the source
  paper is explicit that it is illustrative, not a build authorization.
- None of these steps require a vendor selection or a canon change —
  consistent with the AAN CTA's own closing move ("none of this
  requires a specific vendor decision on day one").
- `tic3-sdwan-vs-dia.qmd` is the one case where the paper already has a
  strong action checklist (Part 8); the draft CTA above is intentionally
  short so it doesn't duplicate it.
- Not yet applied to any `.qmd` file. Once approved, each is a single
  self-contained insertion (no reflow of surrounding content needed) —
  candidate for one PR per paper or one PR for all five, matching the
  "each independently reviewable" pattern the 2026-07-26 content memo
  used.
