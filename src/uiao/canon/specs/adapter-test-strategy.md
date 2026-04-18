---
document_id: UIAO_131
title: "UIAO Adapter Test Strategy — Three-Tier Model for a Boundary-Outside Substrate"
version: "1.0"
status: Current
classification: CANONICAL
owner: "Michael Stratton"
created_at: "2026-04-17"
updated_at: "2026-04-17"
boundary: "GCC-Moderate"
---

# UIAO Adapter Test Strategy

## 1. Overview

The UIAO substrate lives **outside** the FedRAMP Moderate
authorization boundary. Every adapter in `modernization-registry.yaml`
and `adapter-registry.yaml` targets systems that live **inside** a
boundary — federal agency tenants, vendor-operated SaaS, on-prem
agency infrastructure. The substrate cannot directly reach those
systems for automated testing.

This spec defines the **three-tier adapter test strategy** that
resolves the testability gap without requiring access to a
production federal environment. It sits under
[UIAO_121](./adapter-conformance-test-plan-template.md) (Adapter
Conformance Test Plan — Template) as the governing test-architecture
document and is consumed by
[UIAO_123](./adapter-integration-test-plan.md) (Adapter Integration &
Test Plan).

## 2. Scope

**Audience:** adapter developers, conformance reviewers, agency
operators evaluating UIAO, auditors assessing adapter maturity.

**Applies to:** every adapter in
`core/canon/modernization-registry.yaml` and
`core/canon/adapter-registry.yaml`, regardless of class
(modernization | conformance) or mission-class.

**Does not apply to:** the substrate walker, drift engine, OSCAL
generator, or any component that operates on canon alone (those are
unit-tested directly in `impl/tests/` against local fixtures).

## 3. The three-tier model

An adapter's conformance is demonstrated across three independent
test tiers. Each tier validates a distinct axis of the adapter's
behavior; none is sufficient alone.

### 3.1 Tier 1 — Live commercial-tenant tests

**What it proves:** the adapter's common-plane logic — API shape,
authentication flow, response parsing, happy-path state transitions
— works against a real live cloud service.

**Target:**

- **Entra ID / M365 adapters** — Microsoft 365 Developer Program
  commercial tenant. Free, 25 E5 user licenses, Entra ID P2
  included, renewable every 90 days on qualified developer
  activity.
- **Self-hosted AD / IPAM / PKI** — Azure VMs running Windows
  Server eval ISOs (or vendor-provided eval appliances) inside a
  developer Azure subscription, stood up via Terraform on demand.
- **Vendor cloud adapters (CyberArk, Palo Alto, ServiceNow, etc.)**
  — each vendor's own developer / evaluation program. Availability
  and scope vary per vendor; documented per-adapter in
  `modernization-registry.yaml`.

**Execution:** nightly CI job, gated on a secret-scoped tenant
credential stored in GitHub Actions. A tier-1 failure blocks the
adapter's conformance status from advancing.

**What it does NOT prove:** GCC-Moderate-specific behavior. The
developer tenant is **commercial cloud**. Feature availability,
telemetry behavior, and data residency differ from GCC-Moderate
per Microsoft's public matrix. Any assertion that the adapter
handles a GCC-Moderate-specific code path cannot be proven by
tier 1.

### 3.2 Tier 2 — Contract tests against recorded fixtures

**What it proves:** the adapter handles GCC-Moderate-specific
behavior correctly — including the feature gaps and
boundary-imposed restrictions that differ from commercial cloud.

**Target:** a set of YAML / JSON fixtures under
`impl/tests/fixtures/contract/<adapter>/` that record expected
requests and responses for each supported operation. Fixtures are
authored from:

1. **Microsoft Learn** documentation citing GCC-Moderate behavior.
2. **Vendor documentation** for GCC variants where published.
3. **Governance findings** (`docs/findings/`) that document known
   boundary constraints.
4. **Historical transcripts** from actual agency deployments where
   the adapter was exercised (sanitized, with agency consent).

Every fixture carries a provenance block naming its source and the
date it was recorded. Fixtures are canonical — they do not drift
silently. A fixture whose upstream source changes is flagged by
the CI drift check (see §5).

**Execution:** part of `pytest.yml` on every adapter PR. Zero
network calls. Fast, deterministic, always runs.

**What it does NOT prove:** that live GCC-Moderate behaves
according to the recorded fixture. Fixtures can go stale when
Microsoft / vendors change behavior. Tier 3 is the counterweight.

### 3.3 Tier 3 — Reference-deployment tests

**What it proves:** the adapter works against a real, live
GCC-Moderate tenant as operated by a partnering agency.

**Target:** an agency that has adopted UIAO, has granted limited
test access to a non-production GCC-Moderate tenant, and has
opted into the reference-deployment program.

**Execution:**

1. Tests run inside the agency's boundary, under the agency's
   ATO, using the agency's operator credentials. UIAO's CI
   infrastructure does **not** hold federal credentials.
2. Results are exported as a signed OSCAL evidence bundle
   (UIAO_113 graph schema) and published back to the substrate's
   evidence layer.
3. A reference-deployment run is gated on a named agency,
   point-of-contact, and scope agreement. No open-call testing
   against federal tenants.

**Execution cadence:** quarterly minimum, per-adapter, or within
30 days of any tier-2 fixture update that affects that adapter.

**What it does NOT prove:** scale. A reference deployment is one
tenant. Multi-tenant / multi-agency coverage expands over time as
more agencies adopt UIAO.

## 4. Adapter conformance gates

An adapter advances through three explicit conformance gates
aligned 1:1 with the tiers. Each gate requires evidence of
test-tier success before the adapter's `status` field in the
registry may advance.

| Registry status | Required gates |
|---|---|
| `draft` | none |
| `alpha` | tier 2 green |
| `beta` | tier 1 + tier 2 green |
| `active` | tier 1 + tier 2 green; at least one tier 3 pass in the past 90 days OR a documented exclusion per §5 |

A registry edit that advances an adapter's status without the
required evidence raises a DRIFT-PROVENANCE finding in the
substrate walker.

## 5. Exclusions and failure modes

### 5.1 Adapters with no reachable test target

Some adapters target systems for which no developer / evaluation
access exists and for which no partner agency has volunteered a
reference deployment. Examples from the current registry:

- `bluecat-address-manager` — BlueCat requires sales contact for
  any access; no public developer sandbox.
- `mainframe` (reserved) — z/OS Connect test fixtures require
  real mainframe infrastructure.

These adapters may remain at `beta` status indefinitely, with an
explicit registry annotation:

```yaml
- id: bluecat-address-manager
  status: beta
  tier-3-exclusion: "No developer / evaluation access available; tier-3 deferred until a partner agency provides a reference deployment."
```

The exclusion is itself a governance finding
(`docs/findings/adapter-no-reachable-test-target.md`) — it
documents a capability gap, not an error.

### 5.2 Tier-1 target unavailability

If a vendor retires its developer program (as has happened
historically), the adapter's tier-1 tests move to a quarantined
path (unlabeled, still runnable on-demand) and the adapter is
noted in the registry as `tier-1-degraded`. The governance
finding names the vendor, the retirement date, and the search
for an alternative test target.

### 5.3 Fixture staleness

A tier-2 fixture older than 365 days is automatically flagged by
the substrate walker as **potential staleness** (not a failure,
but a notification). The flag clears when the fixture is
re-verified against a tier-3 run or re-recorded from a
refreshed upstream source.

## 6. Reporting

Every adapter carries a **test-status footer** on its page in the
Modernization Atlas, auto-generated from the registry:

- Tier 1: green / red / degraded / N/A
- Tier 2: green / red / stale (N days) / N/A
- Tier 3: green / red / pending (N days since last run) / excluded

The footer links to the most recent evidence bundle for each
tier and to the governance finding if an exclusion applies.

## 7. Relationship to the FedRAMP-INR finding

The FedRAMP GCC-Moderate telemetry constraint (documented
separately under `docs/findings/`) is a **tier-2 fixture class**.
Adapters that would interact with INR when operating in
GCC-Moderate must record a fixture showing INR is **unavailable**
and that the adapter handles the unavailability gracefully
(specifically: it does NOT attempt to call a feature that the
documentation confirms is not present). This fixture is validated
against Microsoft Learn citations, not against live INR.

## 8. Non-goals

This strategy does **not**:

- Authorize UIAO to operate inside any federal boundary. UIAO
  remains outside the boundary per the substrate manifest.
- Require any agency to grant tier-3 access. Tier-3 is opt-in.
- Claim tier-1 commercial tests are sufficient for GCC-Moderate
  certification. They are not; see §3.1.
- Define the specific vendor-eval procurement path per adapter.
  That lives in each adapter's `modernization-registry.yaml`
  entry or `adapter-registry.yaml` entry.

## 9. Cross-references

- UIAO_003 — Adapter Segmentation Overview (taxonomy parent)
- UIAO_104 — Test Harness & CI Enforcement Layer (CI substrate)
- UIAO_113 — Evidence Graph Model (output format for tier-3
  evidence bundles)
- UIAO_121 — Adapter Conformance Test Plan — Template (per-adapter
  filled artifact)
- UIAO_123 — Adapter Integration & Test Plan — Canonical Template
- UIAO_124 — Adapter Operations Runbook
- UIAO_126 — Test Plans Program (catalog parent)
- `docs/findings/` — governance findings covering boundary-imposed
  test-target gaps
- `core/canon/modernization-registry.yaml` — per-adapter test-tier
  annotations land here
- `core/canon/adapter-registry.yaml` — same for conformance
  adapters
