# Federal AI Identity Governance: Findings Brief

**To:** Office of the Federal Chief Information Officer (OFCIO)
**Attention:** Gregory Barbaccia, Federal Chief Information Officer
**From:** Michael Stratton — michael.francis.stratton@gmail.com
**Date:** June 2026
**Subject:** 14 Agentic AI Systems Operating Without Authorization — and a Governance Model to Close the Gap

---

## The Finding

I applied an open-source identity governance scanner (UIAO_196, available at
github.com/WhalerMike/uiao) to the 2025 OMB Federal AI Use Case Inventory
against the six identity governance obligations in M-25-21. Across the 1,480
live federal AI systems in the inventory, the scanner produced 1,346 findings.

| Finding type | Systems affected | Share of live |
|---|---|---|
| No Authorization to Operate (`have_ato ≠ Yes`) | **596** | 40% |
| No owner identity anchor (`contact_email` blank) | **488** | 33% |
| PII-bearing system with no Privacy Impact Assessment | **248** | 17% |
| Agentic AI without ATO — immediate governance halt | **14** | <1% |

The 14 agentic systems are the most urgent finding. They are not a warning —
the M-25-21 high-impact compliance deadline of April 15, 2026 has passed.
These are documented compliance failures, not pending risks.

---

## The 14 Agentic Systems

The scanner classifies any system with `ai_type = Agentic AI` and `have_ato ≠
Yes` as a Priority 1 finding: an autonomous actor inside the federal identity
substrate without a governing authorization. Among the 14:

- **DOJ** — Prisoner risk-assessment system (Bureau of Prisons), production since 2023
- **NASA** — Two autonomous mission planners, including the Mars Perseverance rover autonomy layer
- **HHS/CDC** — Automated web scanner
- **DOT** — Public comment analysis system

Each of these systems operates continuously, makes consequential decisions, and
runs under credentials that have no documented owner in the identity layer,
no rotation policy, and no deprovisioning plan on record.

---

## Why This Is an Identity Problem, Not Just an ATO Problem

An ATO governs the system as a technology artifact at a point in time. It does
not govern the identity the system operates under once deployed.

The service account or managed identity the system uses to query databases and
call APIs is the actual access surface. That identity can be:

- **Over-permissioned** — scoped at deployment and never reviewed since
- **Unowned** — the administrator who created it may have left the agency
- **Unrotated** — no rotation policy applies if there is no identity record
- **Ghost credentials** — surviving the system after it is retired, providing
  indefinite access to whatever the system had access to

None of these conditions are visible in the current OMB inventory schema because
the inventory has no fields for identity governance.

---

## The Governance Model

OrgPath is the organizational placement model that already governs human and
device identities in UIAO-compliant deployments. It assigns every identity
object — human, device, or AI system — a position in the bureau hierarchy:

```
DOD:DISA:ai:joint-ai-ops-assistant
HHS:CDC:ai:web-scanner
DOJ:BOP:ai:prisoner-risk-assessment
```

That placement is the anchor for:

| Governance function | Without OrgPath | With OrgPath |
|---|---|---|
| Credential owner | Unknown | Bureau governance contact |
| Rotation policy | None | Bureau service-account standard |
| Access review | Never triggered | Annual, same cycle as human accounts |
| Blast radius on compromise | Unknown | Bounded to OrgPath node |
| Deprovisioning on retirement | Manual / forgotten | Triggered by `development_stage = retired` |

The OMB inventory already contains the fields needed to derive OrgPath: `agency`
maps to the top-level node, `agency_bureau` maps to the bureau node. The gap is
not missing data — it is an unbuilt binding between the inventory record and the
identity governance layer.

---

## The Centralized Deployment Model

This governance model does not require each agency to build its own scanner.
The most direct path to coverage follows the CDM pattern:

1. **OFCIO runs the scanner centrally** against the public OMB inventory CSV
   for all 56 agencies — one scan produces findings for all 1,480 live systems
2. **Agency CISOs receive a structured findings report** — 14 P1 agentic
   systems are flagged for immediate action; 596 ATO gaps and 488 ownership
   gaps are prioritized per agency
3. **Per-agency remediation follows** — agencies assert ownership, rotate
   credentials, and document governance contacts using their existing IGA tooling
4. **Annual inventory refresh drives the lifecycle** — when a system retires in
   the inventory, the deprovisioning workflow triggers automatically

The scanner is available today, requires only the public OMB CSV as input, and
produces structured findings in under two minutes for the full 1,480-system
inventory. No agency-side deployment is required for the OFCIO central scan.

---

## The Schema Gap

The 2026 OMB inventory schema is the right place to close the underlying
recording gap. Four new fields would make the governance model universally
applicable without imposing new compliance burdens — they ask agencies to record
what should already be in their deployment artifacts:

| Field | Description |
|---|---|
| `identity_type` | `managed-identity` / `service-account` / `workload-identity-federation` / `api-key` / `none` / `unknown` |
| `owning_org_unit` | The bureau or office that holds credential ownership responsibility |
| `credential_rotation_policy` | `yes` / `no` / `not-applicable` |
| `identity_governance_system` | Name of the IGA platform tracking the credential, or `none` |

A formal schema extension proposal has been submitted to OFCIO_AI@omb.eop.gov.

---

## What Is Available Today

| Artifact | Location | Description |
|---|---|---|
| Scanner source | `src/uiao/governance/ai_inventory/` | Python, MIT-licensed, no external dependencies for OMB scan |
| PowerShell runbook | `docs/customer-documents/operational-guides/ai-identity-governance/scripts/Invoke-AIInventoryScan.ps1` | Standalone; runs anywhere PowerShell 7 is available |
| Governance narrative | `docs/customer-documents/orgpath-narrative/Book_21.qmd` | Eight-chapter technical brief: the identity surface gap, M-25-21 obligations, OrgPath binding, scanner mechanics, agentic AI tier, lifecycle model |
| Identity record schema | UIAO_196 | 19-field AI system identity record; maps all current OMB inventory fields plus the four proposed additions |
| Governing ADR | ADR-112 | Federal AI Use Case Governance; binds lifecycle states to identity governance obligations |

All artifacts are in the public repository: **github.com/WhalerMike/uiao**

---

## Contact

Michael Stratton
michael.francis.stratton@gmail.com
github.com/WhalerMike/uiao

Available to provide a live demonstration of the scanner against the 2025
inventory, share findings data, or discuss the proposed schema extension and
governance model with OFCIO program staff.
