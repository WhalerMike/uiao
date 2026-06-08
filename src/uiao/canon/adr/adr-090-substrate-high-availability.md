---
adr_id: adr-090
title: "UIAO Substrate High Availability — Hot-Standby Replica with Automatic, Split-Brain-Safe Failover"
status: ACCEPTED
decided: 2026-06-02
deciders: Michael Stratton
updated: 2026-06-02
next_review: 2026-12-02
review_trigger: An active-active (multi-writer) substrate authority is proposed; the witness/quorum or fencing mechanism that gates promotion is changed; the near-zero RPO or single-digit-minutes RTO target is revised; a customer requires sub-minute RTO or zero-RPO synchronous-everywhere guarantees beyond what a two-node + witness topology provides; ADR-041's single-host base posture is itself superseded.
impact: 'Realizes the hot-standby follow-up ADR that ADR-041 deferred (ADR-041 §"Negative / mitigations" and §"Related work"). Establishes that an HA-enabled UIAO substrate runs a hot-standby replica with automatic, witness-gated, split-brain-safe failover, raising the recovery posture from ADR-041''s cold-restore (RPO 24 h / RTO 4 h) and Book_15 Ch5''s narrative (RPO 4 h / RTO 8 h) to a single coherent target of near-zero RPO (synchronous replication) and single-digit-minutes RTO (automatic failover). The single-logical-authority invariant (exactly one node binds commits at any instant) is preserved, not weakened — active-active multi-master remains rejected. Extends, does not supersede, ADR-041; HA is opt-in per customer. Doctrine + reference only: no schema, registry, or runtime change.'
supersedes: null
superseded_by: null
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-090-substrate-high-availability.html
---

# ADR-090: UIAO Substrate High Availability — Hot-Standby Replica with Automatic, Split-Brain-Safe Failover

## Status

**ACCEPTED** — 2026-06-02.

This ADR **extends** [ADR-041](adr-041-uiao-git-infrastructure.md) (the
accepted single-host substrate decision). It does not supersede it: ADR-041
remains the decision of record for the substrate's host platform, web
front-end, authentication, storage, identity model, and hardening. This ADR
adds one thing ADR-041 explicitly deferred — the substrate's **high-availability
posture** — and nothing else. It changes no schema, registry entry, adapter, or
URL.

ADR-041 named this work as pending in two places:

> **Single-host failure domain.** Mitigated by the documented Phase 12 backup +
> manual failover playbook; a hot-standby replica is a follow-up ADR if the
> 4-hour RTO is insufficient for a given customer. — ADR-041 §Negative / mitigations
>
> **Pending follow-up ADR** — hot-standby replication if a customer requires
> sub-4-hour RTO. — ADR-041 §Related work

ADR-090 is that follow-up ADR.

## Context

The UIAO substrate authority is the single on-premises Gitea-behind-IIS host,
inside the customer's GCC-Moderate boundary, on which every canonical artifact
becomes binding at the moment of commit ([ADR-041](adr-041-uiao-git-infrastructure.md);
Book 16, "The Ground Beneath the Path"). Two properties of that host are in
tension, and resolving the tension is the whole of this ADR:

1. **It must be singular in authority.** Book 16 Chapter 3 ("One Host, Not a
   Fleet") and ADR-041 §Context.2 both assert that two machines cannot both
   accept binding commits without producing two histories — divergent truth.
   The single source of truth is, in Book 16's words, *"a physical claim about
   how many machines are allowed to say yes. The answer is one."* Horizontal
   scale, where needed, lives at the **target surfaces** (Entra, Intune, Arc),
   never at the substrate authority.

2. **It must not be a single point of failure.** A governance substrate that
   the whole modernization program depends on cannot have a recovery story that
   is *"reinstall the host and cold-restore from last night's backup."* ADR-041
   set the base posture deliberately low — RPO 24 h / RTO 4 h via cold restore
   into a passive replica, manually triggered — and flagged that a customer with
   a tighter recovery requirement needs more.

The recovery numbers are also **inconsistent across the corpus today**, which
this ADR reconciles:

| Source | RPO | RTO | Failover |
|---|---|---|---|
| ADR-041 §Decision (Backup / DR) | 24 h | 4 h | Manual, cold restore into passive replica |
| Book_15 Ch5 (DR narrative) | 4 h | 8 h | Manual, against a secondary server |
| UIAO_114 (HA layer, control plane) | near-zero (raw evidence) | rebuild-bounded | Active-passive, "manual or automated promotion" |
| disaster-recovery.qmd §2 (Git replica) | 0 (replicated) | 30 min | Active-passive mirror |

Book 16 Chapter 3 already anticipates the resolution. Its rule is not
"never replicate"; it is:

> redundancy that preserves a single answer is safety; redundancy that produces
> two answers is corruption wearing safety's clothes.

A cold standby preserves a single answer because only one host is ever live. The
question this ADR answers is whether a **hot** standby with **automatic**
failover can preserve the same single answer. It can — if, and only if,
promotion is gated so that exactly one node may ever be the writer at one
instant. That gate is the technical heart of this decision.

## Decision

### D1. ADR-090 extends ADR-041; it does not replace it

ADR-041 remains the base substrate decision. ADR-090 adds the HA posture for
deployments that require it. Where the two appear to differ on recovery numbers,
ADR-090's targets (D5) govern an HA-enabled deployment; ADR-041's cold-restore
numbers remain the floor for a non-HA (base) deployment and for total-site-loss
recovery of either.

### D2. The single-logical-authority invariant is preserved

Exactly **one** node accepts a binding commit at any instant. Active-active /
multi-master writing to the substrate authority remains **rejected**, for the
reason Book 16 Chapter 3 and ADR-041 §Context.2 give: two writers produce two
histories. "High availability" here means *the single authority is made
continuously available through redundancy*, not *the authority is spread across
multiple live writers*. This ADR does not loosen the invariant by one inch; it
hardens the machinery that upholds it during a failover.

### D3. Cold standby is upgraded to a synchronously-replicated hot standby

The base ADR-041 posture is a cold passive replica restored on demand. ADR-090
replaces it, for HA-enabled deployments, with a **hot standby** kept
continuously current via **synchronous replication** of both pieces of substrate
state:

- **Relational state.** Gitea's PostgreSQL database (per ADR-041, on a separate
  host) uses synchronous streaming replication (`synchronous_commit = on`,
  `remote_apply` semantics) to a standby PostgreSQL instance, so an acknowledged
  commit is durable on both before it is reported committed.
- **Git + LFS state.** Bare repositories under `D:\GitRepos\` and the LFS object
  store are replicated synchronously to the standby (post-receive mirror to a
  hot peer, or block/volume-level synchronous replication), so the standby's
  refs never trail the primary's acknowledged refs.

The standby runs Gitea + IIS in a warm, ready-but-not-writing state. It does not
serve binding writes while the primary is healthy.

### D4. Automatic failover is split-brain-safe by construction

Failover is **automatic** but gated so it can never yield two writers:

- A lightweight **witness / quorum arbiter** (a third, low-cost node) observes
  both substrate nodes. **Only the node that holds quorum may bind commits.** A
  primary that loses contact with the witness must stop accepting writes; a
  standby may promote **only** after it has acquired quorum.
- The demoted (or partitioned) former primary is **fenced** (STONITH /
  power-or-network isolation, or a hard write-lock) before the standby begins
  binding commits, so a "returning" old primary cannot accept a stray write.
- A **virtual IP / DNS record follows the active node**, so clients,
  server-side hooks, and the GitHub upstream mirror always reach the one writer
  without reconfiguration.

This is the mechanism that lets automatic failover honor D2: the witness makes
"who may say yes" a single, arbitrated answer, and fencing makes the previous
answer-holder incapable of saying yes. This is a deliberate, controlled
promotion in Book 16 Chapter 3's sense — it is *never* both nodes serving writes
at once.

### D5. One coherent recovery target replaces the conflicting numbers

For an HA-enabled substrate:

| Objective | Target | Basis |
|---|---|---|
| **RPO** | Near-zero | Synchronous replication (D3): acknowledged commits exist on both nodes before acknowledgement |
| **RTO** | Single-digit minutes | Automatic, witness-gated promotion (D4) — no human in the failover path |

Cold-restore-from-backup (ADR-041 §Decision; Book_15 Ch5) remains the **floor**
for **total-site loss** (both nodes + witness gone) and for non-HA deployments;
those scenarios retain the documented backup chain and the off-premises GitHub
mirror as last-resort recovery. The GitHub mirror remains **ingest, never
authority** ([ADR-041](adr-041-uiao-git-infrastructure.md) §Decision).

### D6. No single point of failure below the authority tier

HA at the node level is necessary but not sufficient. An HA-enabled substrate
removes single points of failure across the stack: NIC teaming for the network
path, redundant power, and redundant/replicated storage for each node. What is
deliberately **not** made redundant-by-fan-out is the *authority itself* — that
is the single logical writer of D2. Horizontal scale continues to live only at
the target surfaces (Entra, Intune, Arc), per Book 16 Chapter 3.

### D7. HA is opt-in per customer; both nodes are Tier-0 governed objects

The base ADR-041 single-host-with-cold-standby deployment remains valid where a
4-hour RTO is acceptable. HA per this ADR is **opt-in**, selected when a
customer's recovery requirement demands it. When enabled:

- The standby and the witness are classified and hardened identically to the
  primary — Tier-0, CIS Level-2, AppLocker / WDAC, Defender for Servers Plan 2 —
  because a standby that can become the authority must be as trustworthy as the
  authority.
- Each node is a first-class governed object: it carries its own OrgPath, sits
  in an Administrative Unit, and is evaluated by the drift engine on cadence,
  exactly as the single host is in Book 16 Chapter 6 ("From Idea to Iron"). One
  authority, governed once, becomes two identically-governed nodes that are only
  ever one authority at a time.

## Consequences

### Positive

- **Recovery posture matches the substrate's criticality.** Near-zero RPO and
  minutes-scale RTO replace a 4–8 hour cold-restore for the host the entire
  program depends on.
- **The corpus stops contradicting itself on RPO/RTO.** One target, cross-linked
  from ADR-041, Book_15 Ch3/Ch5, UIAO_114, and the DR playbook.
- **The single-truth invariant is strengthened, not traded away.** Split-brain
  is made structurally impossible at failover (witness + fencing), which is a
  stronger guarantee than "manual failover, done carefully."
- **No new operator paradigm.** Witness/quorum, synchronous PostgreSQL
  replication, fencing, and a floating VIP are standard Windows-Server / Gitea /
  PostgreSQL HA primitives the federal operator base already understands.

### Negative / mitigations

- **Added cost and complexity.** A second hot node + a witness, plus
  synchronous-replication latency on the commit path. Mitigated by D7's opt-in
  scoping — customers who do not need sub-4-hour RTO stay on the ADR-041 base
  posture.
- **Synchronous replication couples the nodes' availability.** If the standby
  and witness are both unreachable, the primary must choose safety (stop binding
  writes) over availability to avoid split-brain. This is the correct trade for
  a source-of-truth and is the explicit intent of D2/D4; it is documented so
  operators expect it.
- **Failover testing is now in scope.** Automatic failover must be exercised
  (planned-failover drills) alongside the existing quarterly DR cold-restore
  drills (Book_15 Ch5).

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| **Active-active / multi-master substrate authority** | Two writers produce two histories — the exact divergent-truth failure Book 16 Chapter 3 and ADR-041 §Context.2 reject. Non-negotiable for a source-of-truth. |
| **Keep ADR-041 cold standby only** | Insufficient RTO for customers who depend on the substrate for time-sensitive governance; this is precisely the gap ADR-041 flagged for a follow-up. Retained as the opt-out (D7), not the ceiling. |
| **Hot standby with *manual* failover** | Better RPO but RTO still gated by human response time; does not meet the minutes-scale target. Retained conceptually as the planned-failover path, but automatic promotion (D4) is the decision. |
| **Cloud-managed HA (e.g. managed Postgres HA, geo-redundant PaaS) for the authority** | Excluded by boundary — the substrate authority must sit inside the customer's GCC-Moderate boundary (ADR-041 §Context). Cloud IaaS for the *witness* only may be considered under the ADR-059 commercial-FedRAMP exception pattern, but the writers stay on-premises. |
| **Two writers + post-hoc reconciliation/merge** | Reconciling divergent canon after the fact reintroduces "two plausible histories" and defeats deterministic provenance. Rejected. |

## References

- [ADR-041](adr-041-uiao-git-infrastructure.md) — UIAO Git Infrastructure; the
  base single-host substrate decision this ADR extends, and the source of the
  deferred hot-standby follow-up.
- [ADR-059](adr-059-sailpoint-adapter-family.md) — IaaS commercial-FedRAMP
  exception pattern (relevant only to an optional cloud-hosted witness; the
  writers remain on-premises).
- Book 16, Chapter 3 — "One Host, Not a Fleet"
  (`docs/customer-documents/orgpath-narrative/Book_16_CPT_03.qmd`) — the
  single-authority invariant and the "redundancy that preserves a single answer
  is safety" rule this ADR operationalizes.
- Book 15, Chapter 3 — "Building the Substrate" and Chapter 5 — "Disaster
  Recovery and Platform Resilience" — the narrative surfaces reconciled to this
  ADR's recovery target.
- UIAO_114 — "UIAO High-Availability & Fault-Tolerance Layer"
  (`src/uiao/canon/specs/ha.md`) — the program-level active-passive,
  single-writer HA model this ADR applies to the substrate authority.
- UIAO_117 — "UIAO Recovery Layer" (`src/uiao/canon/specs/recovery.md`) — the
  reconstitution pipeline that backs the total-site-loss floor.
