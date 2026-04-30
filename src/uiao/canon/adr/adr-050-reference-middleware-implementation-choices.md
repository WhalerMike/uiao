---
id: ADR-050
title: "D3.1 Reference Middleware — Runtime, Language, Packaging, and Test Choices"
status: proposed
date: 2026-04-30
deciders:
  - governance-steward
  - identity-engineer
  - security-steward
supersedes: []
related_adrs:
  - ADR-003
  - ADR-004
  - ADR-035
  - ADR-049
canon_refs:
  - UIAO_136_priority1-transformation-project-plans
  - "Spec2-D3.1-APIDrivenInboundProvisioningArchitecture (canon/specs/)"
---

# ADR-050: D3.1 Reference Middleware — Runtime, Language, Packaging, and Test Choices

## Status

PROPOSED

## Context

[ADR-003](adr-003-api-driven-inbound-provisioning.md) accepted
API-driven inbound provisioning via Microsoft Graph `bulkUpload` as
UIAO's canonical HR provisioning path.
[Spec 2 D3.1](../specs/Spec2-D3.1-APIDrivenInboundProvisioningArchitecture.md)
defines the architecture — every component, interface, message, and
failure mode the middleware layer must handle.

D3.1 §3.2 deliberately leaves implementation specifics open:

> **Deployment options** (architecturally equivalent — pick per
> operational fit):
> | Option | When to choose |
> | Azure Functions (Consumption / Premium plan) | Burst-driven; ... |
> | Azure Logic Apps (Standard) | Connector-rich; ... |
> | Containerized service (ACA / AKS) | Sustained throughput; ... |
> | Power Automate (cloud flow) | Simple flows only; not recommended for production scale |

That openness is intentional for the architecture — different agencies
will pick different deployment options based on their operational fit.
But UIAO needs a **reference implementation** so:

1. The architecture is exercised end-to-end against real Microsoft
   Graph endpoints, validating that the contract in D3.1 actually
   composes.
2. New agency deployments have a starting point that demonstrates the
   canonical patterns (provenance emission, retry / quarantine / rate
   limiting, OrgPath calculation, UPN generation) rather than each
   agency reinventing them.
3. The OrgPath calculator (per [ADR-035](adr-035-orgpath-codebook-binding.md))
   and UPN generator (per Spec2-D1.5) become library-level reusable
   modules with their own test surface, decoupled from the runtime.

The reference implementation is not architectural canon — D3.1 is.
But the *choices* it makes (runtime, language, packaging, test
framework) are architecturally meaningful enough that they need to be
ADR-anchored before code lands. Implementation choices that propagate
to 30 agency deployments are not vibes-driven decisions.

This ADR records those choices and the reasoning behind them.

## Decision

### 1. Language: Python 3.12

**Decision:** the reference middleware is implemented in Python 3.12.

**Reasoning:**

- The UIAO repository's primary language is Python (per the
  `src/uiao/` package; Python is the runtime declared on most existing
  modernization adapters: `service-now`, `palo-alto`, `cyberark`,
  `infoblox`, `bluecat-address-manager`, `terraform`, `entra-dynamic-groups`,
  `entra-admin-units`, `entra-device-orgpath`, `entra-policy-targeting`,
  `orgtree-drift-engine`, `active-directory`).
- The two other in-tree Python adapters that touch identity surfaces
  (`entra-id` and `m365`) declare `runtime: powershell-7.4`, but those
  predate the OrgTree work. The post-OrgTree convention is Python.
- Python's library ecosystem for SCIM 2.0 + Microsoft Graph + Azure
  Functions is mature.
- Type-checking via mypy is already part of UIAO CI; the reference
  middleware inherits that gate.

**Rejected alternative:** PowerShell 7.4. Rejected because it does not
match the post-OrgTree adapter convention and because the OrgPath /
UPN calculator extraction (see Decision 5) is significantly cleaner
in Python given UIAO's existing test patterns.

**Rejected alternative:** TypeScript / Node. Rejected because it would
introduce a second language ecosystem to UIAO maintenance with no
offsetting benefit.

### 2. Runtime: Azure Functions (Python, Consumption or Premium plan)

**Decision:** the reference middleware deploys as Azure Functions on
the Python runtime. Initial reference is Consumption plan; agencies
graduating to sustained-throughput workloads can move to Premium plan
without code change.

**Reasoning:**

- Per D3.1 §3.2, Azure Functions is the canonical choice for the
  burst-driven HR-event pattern that UIAO's HR-agnostic-via-middleware
  design implies.
- Azure Functions on Python deploys to Azure Government regions,
  satisfying GCC-Moderate posture per ADR-003.
- Managed identity binding to Azure Key Vault (for the §4.1
  service-principal certificate) is built in.
- The HTTP-triggered + queue-triggered hybrid model maps cleanly to
  D3.1's middleware contract: HTTP triggers handle HR-adapter pushes,
  queue triggers handle retry + quarantine flows.

**Rejected alternative:** Logic Apps Standard. Rejected for the
reference impl because its connector-first model obscures the
canonical patterns (provenance emission, OrgPath calculator hook) that
the reference is meant to demonstrate. Logic Apps remains a valid
option for agencies per D3.1 §3.2; it is just not the pattern UIAO
ships.

**Rejected alternative:** Container Apps / AKS. Rejected for the
reference impl because the burst-driven workload doesn't justify the
operational overhead. Containerized deployment remains a valid option
for agencies with sustained-throughput needs per D3.1 §3.2.

**Rejected alternative:** Power Automate. Already excluded by D3.1
§3.2 as not production-suitable.

### 3. Packaging: pip-installable subpackage of `uiao`

**Decision:** the reference middleware ships as `uiao.middleware.scim`
inside the existing `uiao` package, not as a separate distributable.
Per the `src/uiao/` consolidated-package layout established by
ADR-032, every UIAO-built component lives inside the single
distribution.

**Reasoning:**

- Existing convention: `src/uiao/adapters/`, `src/uiao/governance/`,
  `src/uiao/cli/`, etc. all live in the same package. The middleware
  is one more module under that root.
- Reusable components (OrgPath calculator, UPN generator) live as
  sibling modules: `uiao.middleware.orgpath`, `uiao.middleware.upn`.
  The Functions runtime imports them via the same package path; tests
  import them the same way.
- Deployment to Azure Functions packages the relevant subset of `uiao`
  — Functions tooling supports Python wheel deployment natively.

**Rejected alternative:** standalone `uiao-scim-middleware` package.
Rejected because it would create a circular dependency with `uiao`
(the middleware needs the OrgPath calculator and the canon-loader)
and would fragment the test surface.

### 4. Test framework: pytest (matches repo)

**Decision:** the reference middleware uses pytest, with the existing
UIAO test conventions (fixtures in `tests/conftest.py`, integration
tests gated by `[integration]` mark).

**Reasoning:**

- Repo-wide convention. No further analysis required.
- Specific posture: every transformation module (OrgPath calculator,
  UPN generator, schema normalizer hook) MUST have unit tests with
  ≥90% coverage measured on the module. Integration tests against a
  real Entra tenant are gated separately and run only in the
  agency-deployment validation phase (D5.1), not on every PR.

### 5. OrgPath calculator and UPN generator extraction

**Decision:** both the OrgPath calculator (per ADR-035 / ADR-048 /
Spec2-D1.2) and the UPN generator (per Spec2-D1.5) are extracted
into testable Python modules within the middleware package, with no
runtime dependencies on Azure Functions or Microsoft Graph. They are
pure-data transforms.

**Reasoning:**

- D3.1 §3.2 explicitly identifies these as the load-bearing
  transformation logic. Keeping them runtime-independent is what
  makes them testable.
- Existing in-flight PowerShell at
  [`tools/discovery/Spec2-D1.5-New-UPNGenerationRules.ps1`](../../../../tools/discovery/Spec2-D1.5-New-UPNGenerationRules.ps1)
  is canonical for the algorithm. The Python module ports the same
  rules; canonical algorithm ownership is the PowerShell at landing
  time, with the expectation that both implementations will reconcile
  to a shared spec when the canonical-algorithm canonization happens
  (UIAO_NNN allocation forthcoming).
- 80+ diacritic transliteration table (per Spec2-D1.5) is a static
  data structure; both implementations import the same canonical
  YAML.

**Module locations:**

- `uiao.middleware.orgpath` — OrgPath calculation; consumes the
  [`canon/data/orgpath/codebook.yaml`](../data/orgpath/codebook.yaml)
  via `importlib.resources` (matches existing UIAO pattern).
- `uiao.middleware.upn` — UPN generation; consumes a yet-to-be-allocated
  canonical diacritic transliteration table.
- `uiao.middleware.scim` — SCIM payload builder; consumes the two
  modules above plus the canonical attribute schema (Spec2-D1.1,
  forthcoming).
- `uiao.middleware.functions` — Azure Functions entry points
  (HTTP + queue triggers).

### 6. Authentication: service principal with certificate, stored in Key Vault

**Decision:** the reference middleware authenticates via service
principal + X.509 certificate stored in Azure Key Vault, accessed via
the Functions managed identity. Client secrets are not supported.

**Reasoning:**

- Matches D3.1 §4.1 ("Client secrets MUST NOT be used").
- Matches [ADR-004](adr-003-api-driven-inbound-provisioning.md) (workload-identity-federation
  default).
- Functions managed identity → Key Vault binding is the standard
  Azure pattern; no custom auth code in the middleware.
- Cert rotation per D3.1 §4.1 (90-day default with overlap window) is
  handled by Key Vault rotation policy + cert reload on Functions
  cold-start.

### 7. Provenance sink: Azure Storage Append Blob (default)

**Decision:** the reference middleware emits provenance records to
Azure Storage Append Blob by default, matching D3.1 §8.4's recommended
sink. The sink is configurable via app setting; agencies can swap to
Event Hub or the UIAO Governance OS native sink without code change.

**Reasoning:**

- Append Blob is cheap, durable, immutable per blob, and supports the
  7-year retention required by Spec 2 §Phase 5 §D5.3 via blob
  versioning + lifecycle policies.
- Configuration-driven sink choice means the reference impl
  demonstrates the canonical pattern without committing agencies to a
  specific sink.

## Consequences

### Positive

- **One canonical implementation** of the load-bearing transformations
  (OrgPath calc, UPN generation, SCIM payload construction). Agencies
  start from a tested, governed module set; they don't reinvent the
  algorithms per deployment.
- **Reference impl exercises the D3.1 contract end-to-end** against
  real Graph endpoints, validating that the architecture composes.
- **The OrgPath / UPN modules are runtime-independent**, so they can
  be reused by future tooling (validation scripts, drift detectors,
  audit utilities) without dragging in Azure Functions dependencies.
- **Type-checked + tested + drift-monitored** — the reference impl
  inherits UIAO's existing CI gates (mypy, pytest, ruff, substrate
  drift). New code is held to the same bar as everything else under
  `src/uiao/`.

### Negative / costs

- **Locking to Azure Functions Python** for the reference means
  agencies that prefer Logic Apps or containers must port the SCIM
  payload construction logic. The architectural-equivalence claim in
  D3.1 §3.2 is preserved but the porting cost is non-zero.
- **Two implementations of UPN generation** (PowerShell at
  Spec2-D1.5-New-UPNGenerationRules.ps1, Python at
  uiao.middleware.upn) until the algorithm is canonized in
  language-neutral form (deferred to future ADR). This is a known
  drift-risk surface.
- **Reference impl operational ownership** — the reference is UIAO-
  maintained code that must be updated when Microsoft Graph changes,
  when Spec 2 deliverables change the canonical schema, or when
  ADR-035 / ADR-048 update OrgPath semantics. The maintenance burden
  is real and is borne by UIAO.

### Risks

- **Microsoft Graph API breaking change.** Mitigated by D3.1 §3.3
  invariant ("read endpoint from Graph metadata at runtime") and by
  pinning Microsoft Graph SDK versions in the pyproject.
- **Functions runtime EOL.** Python 3.12 is supported on Azure
  Functions through at least 2027 per Microsoft Learn (verified
  separately at deployment time). Migration to Python 3.13+ when
  Functions adds support is a routine maintenance task.
- **Cert rotation failure.** Mitigated by overlap-window posture in
  D3.1 §4.1; reference impl implements the failure-mode test case
  and surfaces cert-expiry-in-30-days as an alerting metric.

## Follow-on work

Three PRs land the reference implementation, in this order:

1. **PR — `uiao.middleware.orgpath` + `uiao.middleware.upn` modules.**
   Pure-data transformation modules with full pytest coverage.
   Independent of Azure Functions; can be developed and shipped first.
   Decision 5 above.

2. **PR — `uiao.middleware.scim` payload builder.** Builds SCIM 2.0
   bulk payloads from canonical input records using the modules from
   PR #1. Pure-data; no Graph API calls. Includes property-based tests
   for SCIM RFC 7643 conformance.

3. **PR — `uiao.middleware.functions` Azure Functions entry points.**
   HTTP + queue triggers, Microsoft Graph client with token cache,
   provenance emitter, retry / quarantine logic, rate limiter
   matching D3.1 §7.2. Includes Functions deployment manifest
   (`function_app.py` + `host.json`) and a deployment runbook.

Each PR carries a per-module test plan and lands the corresponding
tests in the same PR (per UIAO convention — "code without tests is
not accepted").

A fourth PR may be needed for a canonical algorithm doc (UIAO_NNN
allocation) that the PowerShell and Python implementations both cite,
closing the §Negative two-implementations-of-UPN-generation drift
risk. That allocation is deferred to v1.1 of this ADR.

## Notes

- This ADR is deliberately scoped to *implementation choices*, not
  *implementation behavior*. Behavior is in D3.1; choices are here.
  If a future PR proposes deviating from one of these choices (e.g.,
  shipping a TypeScript variant), this ADR is the gate that
  proposal must clear.
- The "PowerShell vs. Python" choice for the UPN generator is the
  most contentious of these decisions. PowerShell wins on
  consistency-with-Spec2-D1.5; Python wins on runtime convergence
  with the rest of the middleware. Decision 5 chose Python for the
  middleware while preserving the PowerShell as the algorithm
  reference until UIAO_NNN canonization. Reasonable people may
  disagree; the decision is reversible by ADR amendment.
