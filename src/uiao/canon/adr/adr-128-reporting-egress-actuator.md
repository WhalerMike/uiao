---
adr_id: adr-128
title: "Reporting-Egress Actuator — Gated Outward Submission of ConMon Evidence to Federal Destinations"
status: PROPOSED
decided: null
deciders: Michael Stratton
updated: 2026-07-09
next_review: 2027-01-09
review_trigger: A destination driver is wired to a live government endpoint (CDM API, CyberScope, CLAW, FedRAMP repository, CISA SBOM inbox, CISA incident portal); the in/out-of-boundary decision for the platform actuator is made; an autonomous (L4) submission class is ever proposed (must be refused at Moderate); ADR-092 actuation ladder is amended
supersedes: null
superseded_by: null
publish_to_site: false
publication_style: include
published_at: null
impact: 'Introduces the reporting-egress actuator: an integration-class (change-making) capability that submits already-generated ConMon evidence outward to external federal destinations. Extends ADR-092 actuation to outward submissions, with dry-run as the default, an explicit L3 human-approval gate on every live submission, and no autonomous (L4) path at Moderate. Adds the src/uiao/reporting_egress framework, the `uiao report` CLI group, and five stub destination drivers (cdm, cyberscope, fedramp-repo, cisa-sbom, cisa-incident). Raw telemetry to NCPS/CLAW is explicitly out of scope (native pipe; UIAO attests, does not carry). Formal landing binds the drivers into the modernization (integration) registry and decides the Server-vs-SaaS deployment posture.'
---

# ADR-128: Reporting-Egress Actuator — Gated Outward Submission of ConMon Evidence

## Status

**PROPOSED** — 2026-07-09

Extends **ADR-092** (Active Governance actuation ladder) to a new operation
class: *outward submission of evidence*. Respects **ADR-066** lane discipline
(the governance plane never becomes the network data plane). Companion design:
`specs/reporting-egress.md` (UIAO_208).

## Context

UIAO today **generates and exports** ConMon evidence to local files — `uiao oscal
bundle`, `uiao conmon export-oa`, `uiao conmon dashboard`, the ScubaDrift verdict
pipeline. It does **not** transport that evidence to the external federal
destinations that actually consume it: the CDM Agency Dashboard, CyberScope (FISMA),
the FedRAMP repository (20x / monthly ConMon), the CISA SBOM inbox (BOD 26-04), and
the CISA incident portal. The transport is done today by agency staff (manual upload,
email) or by native tooling (CDM integrators, cloud log forwarders).

The Federal ConMon Reporting Reference (inbox integration set #6) mapped, per
requirement, what AAN alone supplies vs. what AAN + UIAO could supply — and the
"file / stream / transport" column is entirely unbuilt. This ADR decides whether and
how UIAO takes on that transport.

A submission to CISA/OMB is a **write to an external system** — an *actuation* in
ADR-092 terms — not a violation of the ADR-066 lane discipline, which concerns the
*network* data plane (tunnels, routes, packets). The question is therefore not
"may UIAO actuate outward" (the ladder already governs actuation) but "at what rung,
with what gate, and where does the deployment sit."

## Decision

Introduce a **reporting-egress actuator**: an `integration`-class (change-making)
capability that submits already-generated evidence outward, under these invariants.

1. **Dry-run is the default.** `uiao report submit` plans and validates a submission
   without transmitting unless explicitly told to go live. (ADR-040 dry-run doctrine.)
2. **Every live submission is L3-gated.** A live submission requires an explicit
   human **approval token** (approver identity, timestamp, operation). No approval →
   the submission is *blocked*, never sent. This encodes the ADR-092 federal L3
   ceiling directly in the engine.
3. **No autonomous (L4) path at Moderate.** There is no code path that transmits
   outward without a live flag *and* an approval token. Outward submission to a
   government system is a high-consequence, hard-to-reverse, externally-visible act;
   it is permanently L3-capped under this ADR.
4. **Serving read-only status is not egress.** Serving the latest KSI status over an
   API / static URL writes nothing to production and is a separate, ungated,
   continuous L1–L2 function (existing `uiao.api`). It is explicitly *not* governed
   by the L3 gate.
5. **Raw telemetry to NCPS/CLAW is out of scope.** High-volume SIEM/EINSTEIN log
   streaming is data-plane plumbing that stays on the native cloud pipe. UIAO
   *governs and attests* that feed's config and health; it does not carry it.
   Operating the forwarder would edge toward a data-plane position (ADR-066).
6. **Destination drivers are pluggable and ship unconfigured.** Each destination
   (cdm, cyberscope, fedramp-repo, cisa-sbom, cisa-incident) is a driver with a
   `configured` flag defaulting to `False`. A live, approved submission against an
   *unconfigured* driver is *blocked* with "endpoint not configured" — the scaffold
   never simulates a successful government submission. Wiring a live endpoint
   (real URL, credentials, mutual TLS) is a per-destination landing task gated on
   security review and the boundary decision below.
7. **Deployment posture is a boundary decision, not a code decision.**
   - *Platform Server (in-boundary)* is the clean path: it runs inside the agency
     ATO boundary, holds the agency's submission credentials, and files on the
     agency's behalf. Its own integrity (SA-family, immutable audit, break-glass)
     enters assessment scope and must be designed before any live submission op.
   - *SaaS (UIAO-operated)* may serve read-only and generate, but the moment agency
     ConMon evidence transits it to reach CISA it must carry its own FedRAMP
     authorization. Higher lift; deferred behind the boundary decision.

## Consequences

- UIAO gains a **gated reporting actuator** — the "file/transport" leg of ConMon —
  without becoming the network data plane and without any autonomous submission.
- The framework is testable and safe today (dry-run default; unconfigured drivers
  cannot transmit); live value arrives per-destination as endpoints are wired under
  review.
- **Formal landing tasks** (not in this scaffold): register the five drivers in the
  modernization (integration) registry; add credential handling out of canon (canon
  stays read-only per UIAO-SSOT); wire each live endpoint behind the boundary
  decision; add the approval token to the immutable audit trail (SA-family).
- Publication: this ADR is `publish_to_site: false` until the boundary decision is
  taken and at least one driver is live-wired under review.

## Reconciliation

- **ADR-092** — this is a new actuation operation class, permanently L3-capped;
  consistent with the "high-blast-radius classes are L3-capped" rule (an errant
  submission to a federal system is high-consequence).
- **ADR-066** — no network-data-plane position is taken; the one thing that would
  cross that line (carrying CLAW telemetry) is explicitly excluded.
- **UIAO-SSOT** — canon stays read-only; the actuator reads generated artifacts and
  transmits them; it does not mutate canon.
