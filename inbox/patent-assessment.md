# Patent Assessment — *Boundary Router and Active Governance Control Plane for Distributed Computing Systems*

> **Status:** Agent-authored draft in the `inbox/` scratch surface. **Not canon.** Not legal advice.
> Prepared 2026-06-08 to inform a conversation with a registered patent attorney. Nothing here is a
> substitute for a professional patentability search and a formal freedom-to-operate / patentability
> opinion.
>
> **Scope:** (1) substantive assessment of the uploaded draft application; (2) a public-disclosure
> date audit of `WhalerMike/uiao` against the application (the §8 "statutory-bar" check); (3) additional
> inventions in the UIAO codebase that may be independently patentable.

---

## 1. What the application claims (one breath)

A two-plane system: **Boundary Routers** at each domain perimeter (intercept L4–L7 traffic, verify
identity via mTLS/JWT/SPIFFE, enforce signed/versioned *policy bundles*, transform/route/log), governed
by an **Active Governance Control Plane (AGCP)** (policy repository, heartbeat discovery, push/pull
distribution, telemetry aggregation, compliance evaluation, automated remediation, and a federation
gateway for hub-free multi-domain trust). Three independent claims — system (1), method (10), CRM (17)
— plus 17 dependents.

The disclosure is well-written and internally consistent. **Technical quality is high; patent-strategy
risk is where the exposure concentrates** — and a public-disclosure problem (Section 6) now dominates
the analysis.

## 2. Verdict at a glance

| Dimension | Rating | One-line |
|---|---|---|
| Spec clarity / enablement (§112) | **Strong** | Reads like a real architecture; PHOSITA could build it. |
| Subject-matter eligibility (§101) | **Moderate risk** | Functional "engine/orchestrator" claiming of an abstract governance idea; partly saved by concrete network mechanics. |
| Novelty (§102) | **Weak as drafted** | Core building blocks are admitted or off-the-shelf prior art. |
| Non-obviousness (§103) | **Weak as drafted** | The Background section itself supplies the obviousness combination. |
| Claim enforceability | **Significant defect** | Divided-infringement exposure in claims 1 and 10; no standalone AGCP claim. |
| Formal compliance | **Minor fixes** | Abstract over length; placeholders; drawings not embedded. |
| **Inventor self-disclosure** | **🔴 HIGH — urgent** | The public `WhalerMike/uiao` repo + docs site discloses overlapping subject matter as early as 2026-04-18. See Section 6. |

**Bottom line:** a strong invention disclosure whose claims read close to "a service-mesh control plane,
but at the boundary, with a compliance feedback loop." Patentable **with narrowing** — but the public
disclosure clock is already running and must be triaged before anything else.

## 3. Prior art — the building blocks are largely known (and partly admitted)

The Background admits Envoy, the **xDS** protocol, sidecar meshes, and OPA. Helpful for §112; dangerous
for §103. Element-by-element the claimed components map onto existing systems:

- **"Policy bundle" — signed, versioned, distributed.** Open Policy Agent ships a feature literally
  called **bundles** — versioned, **cryptographically signed**, distributed/polled. Closest single hit;
  collides with claim 20 almost verbatim.
- **Control plane pushing policy + collecting telemetry over a stream.** Istio/**Istiod** + xDS does
  exactly this; telemetry v2 collects enforcement/traffic data; SPIFFE/**SPIRE** supplies identities.
  Claim 1's AGCP↔router relationship is the istiod↔Envoy relationship with perimeter placement.
- **Compliance/drift detection + automated remediation.** Google **Anthos Config Management / Config
  Sync** detects config drift and auto-corrects; GitOps reconcilers (Argo CD, Flux) close the loop.
- **Hub-free cross-domain federation sharing trust anchors.** **SPIFFE Federation** shares trust
  bundles across trust domains; **HashiCorp Consul mesh gateways** federate datacenters without a hub.
- **Boundary/edge placement, default-deny, identity-based policy.** Mesh **ingress/egress gateways**;
  Calico/Cilium default-deny network policy.

**Implication:** novelty cannot rest on any single component; it must rest on the *specific combination*
and a *specific technical mechanism*, and the claims must be amended to foreground that.

## 4. Where the genuine novelty likely lives (and how to claim it)

The most defensible inventive concepts in the disclosure are **under-claimed or unclaimed**:

1. **Shadow-traffic inference tied to perimeter placement** — telemetry-derived detection of traffic
   crossing a boundary through *no registered router* (spec ¶[0016]). Freshest idea; appears in **no
   claim**. Build a claim around it.
2. **Three operational modes with a *signed, policy-distributed offline allowlist*** (¶[0028]–[0030]):
   the default-deny fallback's allowlist is itself a governed, distributed artifact. Only thinly covered
   by claims 5/14/19.
3. **Real-time revocation push + continuous per-session re-evaluation** (¶[0023]): AGCP pushes
   CRL/trust-anchor deltas to collapse revocation latency, re-evaluating long-lived streams mid-session.
   Concrete and **not claimed at all**.

## 5. Claim-drafting issues (concrete)

- **Divided infringement — most important fix.** Claim 1 requires *both* Boundary Routers *and* the
  AGCP; claim 10 recites steps performed by the router *and* "receiving, **at the AGCP**…". If a customer
  runs routers and a vendor runs the control plane (or vice versa), no single entity performs all steps →
  direct-infringement gap (*Akamai/Limelight*). **Fix:** add single-actor claim sets — (a) Boundary-Router-only
  apparatus, (b) **AGCP-only apparatus** (currently missing entirely — a competitor selling only the
  control plane may infringe nothing), (c) method claims written wholly from each actor's perspective.
- **§112(f) means-plus-function exposure.** "Policy enforcement **engine**," "remediation
  **orchestrator**," "telemetry **exporter**," "identity **verifier**" are nonce-style nouns + "configured
  to." A court could read these as means-plus-function, limited to disclosed structure — and the spec
  describes them mostly by *function*, not algorithm, raising an indefiniteness risk. **Fix:** claim as
  concrete structures (processors executing specified steps) or disclose a definite algorithm for each.
- **No standalone control-plane claim** — real coverage hole (see above).
- **Minor antecedent basis:** claim 1 introduces "one or more active policy bundles" then "an active
  policy bundle." The Markush "group consisting of allow, deny, transform, quarantine, log" is correctly
  closed — good.
- **Dependent claims** 2 (ABAC/RBAC) and 3 (JWT/mTLS/SPIFFE) recite admitted prior art; fine as
  fallbacks, won't carry novelty.

## 6. 🔴 Public self-disclosure audit — the urgent finding

**The `WhalerMike/uiao` repository is PUBLIC** (GitHub API `"visibility":"public"`, Apache-2.0, public
docs site at <https://whalermike.github.io/uiao/>), created **2026-04-16**, first commit **2026-04-18**.
It publicly discloses subject matter that overlaps materially with the application — including the very
"closed-loop / control-plane-governs-data-plane" concepts identified in Section 4 as the strongest
novelty. Under AIA §102, an inventor's own public disclosure starts a **12-month U.S. grace period** and,
in most foreign jurisdictions (absolute novelty, **no grace period**), is an **immediate bar** unless a
priority application was filed *before* the disclosure.

### Overlapping public disclosures and their dates

| Public artifact (all `publish_to_site: true` → on the GitHub Pages site) | First public | Discloses (maps to patent element) |
|---|---|---|
| `specs/Platform-Overview.md` (UIAO_101) — "Compliance Orchestrator with closed-loop automation" | **2026-04-18** | AGCP compliance evaluator + remediation loop (claims 1, 10) |
| `specs/Platform-Services-Layer.md` (UIAO_102) — Enforcement Marketplace; adapters advertise `controls_supported`, `side_effects`, `blast_radius`, `rollback_capable` | **2026-04-18** | Enforcement actions + remediation/rollback (claims 1, 9, 15) |
| `specs/zero-trust.md`, `specs/governance.md` | **2026-04-18** | Zero-trust enforcement model (FIG. 7; claims 3, 12) |
| `data/control-planes.yml` — six provider-neutral control planes; "Zero Trust Policy Engine… Continuous Access Evaluation… policy decisions exported to SD-WAN + Telemetry" | **2026-04-18** | Control-plane/data-plane split; per-request continuous evaluation |
| `UIAO_006_AODIM_Architecture_v1.0.md` — attribute-driven identity addressing | **2026-04-22** | Identity-context evaluation; ABAC (claims 2, 13) |
| `adr-040-drift-engine.md` — six-phase orchestrator (Snapshot, Compare, Classify, Alert, Remediate, Verify), `dry_run` default, `halt_on_critical`, per-facet `auto_remediate`, governance-review gating | **2026-04-20** | Compliance evaluator + remediation orchestrator + human-in-the-loop (claims 1, 9, 15) |
| `adr-066-application-aware-networking-and-token-bound-transport.md` — application-aware networking, per-call token-bound transport, identity-as-boundary, SD-WAN/SASE/ZTNA governance | **2026-05-12** (dated 2026-05-05) | Boundary-router data plane; per-request identity-bound enforcement (claims 1, 10, 17) |
| `adr-092-active-governance.md` — "Active Governance: control-plane-governs-data-plane," provider-incorporation contract, **L0–L4 actuation maturity ladder** with federal **L3** human-approval ceiling | **2026-06-02** | The AGCP closed-loop posture + automated-vs-gated remediation (the patent's core thesis) |

The term **"Active Governance"** — the application's own AGCP name — is the title of a public ADR
(ADR-092) authored by the named inventor on 2026-06-02. The reconciliation loop (drift → classify →
remediate → verify) that underpins the AGCP's compliance evaluator and remediation orchestrator has been
public since **2026-04-20**.

### What this means

- **U.S.:** A 12-month grace-period clock is running from the **earliest** overlapping disclosure
  (~**2026-04-18**). A U.S. non-provisional (or provisional) covering the disclosed subject matter should
  be filed **no later than ~2027-04-18**, and ideally now. Each *new* public commit that adds claimable
  detail can reset relevant scope, but do not rely on that — treat 2026-04-18 as the hard U.S. deadline.
- **Foreign / PCT:** Most jurisdictions have **no grace period**. Unless a priority application was filed
  **before 2026-04-16**, foreign rights to the *disclosed* subject matter are likely **already
  compromised**. The genuinely novel, *un-disclosed* claim hooks in Section 4 may still be foreign-eligible
  if filed before they are published.
- **The provisional placeholder must be resolved immediately.** The draft says it "claims the benefit of
  U.S. Provisional No. [PROVISIONAL APPLICATION NUMBER], filed [FILING DATE]." **Confirm whether a
  provisional was actually filed and its exact date.** That single fact determines whether priority
  predates the 2026-04-16 public disclosure and therefore whether foreign rights survive.

### Immediate actions (priority order)

1. **Establish the true priority date.** Locate the provisional (number + filing date) or confirm none
   exists. This gates everything below.
2. **If no priority application predates 2026-04-16:** file a U.S. application covering the disclosed
   subject matter now (grace period applies); accept that foreign rights to disclosed matter are likely
   lost; and **file before publishing** any of the still-unpublished novelty in Section 4 / Section 7 to
   preserve foreign eligibility for those.
3. **Freeze further public disclosure** of unclaimed inventive detail (Sections 4 and 7) until filings
   are in. New public commits/ADRs/docs-site pages are printed publications.
4. **Build a disclosure log** mapping each intended claim element to the earliest public commit/date, so
   counsel can assess grace-period coverage element-by-element. (Use `git log --reverse -- <path>` per
   file; the table above is a starting point.)

## 7. Additional potentially-patentable inventions in UIAO

> ⚠️ **Same disclosure caveat as Section 6 applies to every item here — these are already public.** The
> 12-month U.S. grace clock is running from each item's first-commit date; foreign rights are likely
> already barred absent an earlier priority filing. List is for prioritizing what (if anything) still has
> a viable filing path, not an assertion that any item is novel — each needs a search.

1. **Cross-plane identity-addressing overlay ("OrgPath" / AODIM).** A single canonical address (a
   multi-facet attribute schema — "Model C, 15 facets") by which the *same* governed object is resolvable
   uniformly across **identity, network, endpoint, telemetry, and security** control planes, with **access
   computed from attributes rather than assigned** (`UIAO_006`, first public 2026-04-22). The "one
   address resolves an object across heterogeneous control planes" overlay is the namesake of the project
   and is more distinctive than the boundary-router claims. Potential standalone application. Prior art to
   clear: ABAC (NIST SP 800-162), SCIM, SPIFFE IDs, enterprise IGA attribute-based access.

2. **Five-class drift taxonomy + immutable drift ledger applied to *governance artifacts*.** Classifying
   divergence as `DRIFT-SCHEMA` / `DRIFT-SEMANTIC` / `DRIFT-PROVENANCE` / `DRIFT-AUTHZ` / `DRIFT-IDENTITY`
   over an append-only, tamper-evident ledger (`adr-009`, `adr-012`, drift taxonomy). The **DRIFT-PROVENANCE**
   class — detecting divergence between *published documentation* and its *canonical source* ("substrate
   drift") — is unusual; continuous doc-vs-source provenance drift detection in CI is not a common
   technique. Potential method/CRM claim. Prior art: config-drift tools, doc linters, GitOps reconcilers.

3. **Actuation maturity ladder (L0–L4) as a per-operation, policy-gated autonomy governor** (`adr-092`).
   A declared per-operation-class autonomy rung (Record → Observe → Advise → Gated actuation → Autonomous)
   with an environment-scoped ceiling (federal default L3) enforced by the control plane. Framed as a
   *mechanism that bounds automated remediation per operation by declared blast-radius/rollback metadata*,
   it could strengthen the remediation claims in the main application (a useful dependent-claim family
   there) rather than stand alone. Prior art: change-management/approval workflows, autonomy levels in
   other domains.

4. **Token-bound, application-aware transport plane (per-call token transport)** (`adr-066`, first public
   2026-05-12). Binding each transport call to an identity-derived, short-lived token rather than a
   long-lived session, governed by the same control plane. Overlaps the main application's per-request
   zero-trust model and could be folded in as additional claims; on its own, watch token-binding prior art
   (RFC 8705 mTLS-bound tokens, DPoP/RFC 9449, GNAP).

5. **Provider-incorporation contract** (`adr-092`): a uniform adapter contract (bind to one control-plane
   slot; expose `plan/apply/reconcile`; carry the cross-plane address; advertise
   `controls_supported/side_effects/blast_radius/rollback_capable`; declare an autonomy rung) by which a
   third-party data-plane provider is *governed* without being reimplemented. This is more product
   architecture than patentable mechanism, but the **machine-readable governance-metadata contract driving
   automated-remediation eligibility** is the patent-eligible kernel if any.

**My ranking of filing-worthiness:** (1) OrgPath cross-plane overlay > (2) provenance-drift detection >
(4) token-bound transport ≈ (3) autonomy ladder (better as dependents in the main app) > (5) provider
contract. All gated by the search and the priority-date question in Section 6.

## 8. Recommended next steps (consolidated)

1. **Resolve the provisional/priority-date question immediately** (Section 6) — it gates U.S. timing and
   the entire foreign-rights question.
2. **Freeze public disclosure** of the unclaimed novelty (Sections 4, 7) until filings are in.
3. **Professional prior-art search** focused on OPA bundles, Istio/xDS, Anthos Config Sync drift
   remediation, SPIFFE federation, Consul mesh-gateway federation, Tetrate TSB — plus, for Section 7,
   NIST SP 800-162 ABAC, RFC 8705/9449 token binding.
4. **Re-architect the claims:** add AGCP-only and router-only single-actor claim sets (kill divided
   infringement + the coverage gap); add claims to the genuine novelty (shadow-traffic inference,
   distributed signed offline allowlist, revocation-delta push + mid-session re-evaluation).
5. **Inject technical mechanism** (algorithms for compliance scoring, drift detection, remediation
   selection) into spec and narrow claims to shore up §101 and §103.
6. **De-risk §112(f):** reword "engine/orchestrator/verifier" or back each with a disclosed algorithm.
7. **Fix formals:** trim abstract to ≤150 words; finalize the seven drawings; fill docket/provisional
   placeholders.

## Appendix — Recommended claim additions (drafting sketch, for attorney refinement)

> Illustrative only — not filing-ready language.

**A. Standalone AGCP apparatus (closes the coverage gap; single actor):**
> *An apparatus for governing a plurality of boundary routers, comprising one or more processors and
> memory storing instructions that cause the apparatus to: store versioned, cryptographically signed policy
> bundles; register boundary routers via a heartbeat protocol and track each router's operational mode;
> distribute policy bundles over a secure control channel using a hybrid push/pull model with staged
> rollout to a pilot cohort; receive structured enforcement telemetry; compute a per-router compliance
> score by comparing observed enforcement against policy intent; and, upon a detected violation, transmit a
> remediation command selected from rollback, quarantine, alert dispatch, and human-in-the-loop
> escalation.*

**B. Shadow-traffic inference (Section 4.1; novelty hook):**
> *The apparatus of claim A, wherein the compliance evaluator detects, from aggregated telemetry, traffic
> traversing a domain boundary via a path not attributable to any registered boundary router, and reports
> the inferred ungoverned path as a compliance violation.*

**C. Revocation-delta push + mid-session re-evaluation (Section 4.3; novelty hook):**
> *The apparatus of claim A, further configured to push a trust-anchor or revocation delta to registered
> boundary routers upon a revocation event, causing each router to re-evaluate the identity context of
> active long-lived sessions against the updated revocation state without terminating the session.*

**D. Signed, distributed offline allowlist (Section 4.2; novelty hook):**
> *The computer-readable medium of claim 17, wherein the cached policy bundle includes a cryptographically
> signed offline allowlist enumerating a minimal set of permitted communications enforced while the router
> is in a default-deny offline mode, the allowlist being distributed and governed as part of the policy
> bundle.*
