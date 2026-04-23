---
adr: ADR-045
title: "Scan Artifact Redaction Policy for Multi-Agency Distribution"
status: PROPOSED
date: 2026-04-23
author: WhalerMike
supersedes: []
superseded_by: null
related:
  - ADR-025  # Continuous Monitoring Program architecture
  - ADR-043  # FedRAMP RFC-0026 CA-7 integration (pathway posture)
extends:
  - ADR-025
  - ADR-043
tags:
  - fedramp
  - rfc-0026
  - ca-7
  - conmon
  - vulnerability-management
  - redaction
  - multi-agency
  - disclosure
---

# ADR-045: Scan Artifact Redaction Policy for Multi-Agency Distribution

## Status

**PROPOSED — 2026-04-23.** Promoted from the RFC-0026 E7 design draft (`docs/docs/uiao-rfc-0026-e7-scan-redaction-adr-draft.md`) after all four review questions resolved to their recommended defaults. Ratification to `Accepted` is gated on the promotion checklist at the end of this ADR.

## Context

### The disclosure asymmetry

FedRAMP RFC-0026 RV5-CA07-VLN Pathway-2 requires monthly OS / DB / web app / container / service configuration scans to be shared with agency customers. The most-upvoted thread in FedRAMP community discussion #130 — CSP-AB, cb-axon, judgecspab-max, rgaffey, mjprager — flagged that this requirement, as written, is:

1. **Operationally impractical** — in an IaaS-scale tenant, raw scan output runs to terabytes per month.
2. **Actively dangerous** — distributing unredacted exploit-path detail to every agency customer broadens the attack surface: each receiving agency's ingest pipeline becomes a target worth compromising for the exploit intelligence alone.
3. **Internally inconsistent** — the modernized pathway's VDR Balance Improvement Release explicitly prohibits irresponsible vulnerability disclosure, yet the traditional pathway currently imposes no such guardrail.

UIAO runs Pathway-2 per [ADR-043](adr-043-fedramp-rfc-0026-ca7-integration.md) D1 and therefore inherits the distribution requirement. `UIAO_132` §2.3 is silent on how raw scan content should be handled before agency hand-off.

### Where UIAO stands today

- `src/uiao/adapters/vulnscan_adapter.py` + `vulnscan_parser.py` normalize raw scanner output into UIAO's canonical finding shape.
- `.github/workflows/conmon-aggregate.yml` rolls findings into the monthly POA&M CSV and OSCAL drop.
- The E5 multi-agency distribution layer (design draft in PR #177, implementation pending) will fan that rollup out to each agency customer on their declared delivery channel.
- **Nothing in the pipeline today distinguishes between "3PAO-grade evidence" and "agency-grade evidence"** — whatever the normalizer produces is what every consumer sees.

### Why this ADR now

E5 is the point at which redaction decisions become enforceable. Shipping E5 without a redaction policy means UIAO's first monthly distribution ships unredacted exploit-path detail to multiple agencies — exactly what CSP-AB et al. argued against. This ADR defines the policy *before* E5 ships.

## Decision

### D1. Two-tier evidence storage

Every scan artifact is stored in exactly one of two tiers:

- **Tier 1 — Unredacted (3PAO + FedRAMP corrective-action only).** Raw scanner output, plugin identifiers, CVE-to-asset mappings, and exploit-path payloads. Lives under `evidence/raw/<adapter-id>/<yyyy-mm>/`. Access restricted at the repository layer (see D5).
- **Tier 2 — Redacted (agency distribution surface).** The same findings with the sensitive fields stripped per the profile below. Lives under `evidence/distribution/<agency-id>/<yyyy-mm>/` — the location the E5 `distribute.py` script writes receipts to.

Every Tier-2 artifact carries a cryptographic back-reference to its Tier-1 source (sha256 of the raw finding) in a `tier_1_ref` field, so 3PAOs and FedRAMP reviewers who *do* have Tier-1 access can trace any redacted finding back to the original without the redacted file leaking the payload.

### D2. Redaction profile — field allow and deny lists

A finding in Tier 2 **retains** the following fields:

| Field | Rationale |
|---|---|
| `tracking_id` (CSP-assigned) | Primary key for ConMon correlation |
| `risk_level` (critical / high / moderate / low) | Agency SLA trigger |
| `finding_state` (open / closed / deferred / accepted) | POA&M state machine |
| `control_family` (AC / AU / SC / …) | SSP cross-reference |
| `first_observed`, `last_observed` timestamps | Timeliness SLA (ADR-043 D2) |
| `remediation_summary` (≤ 280 chars; see D3) | Agency visibility into CSP posture |
| `planned_completion` date | POA&M CSV column |
| `finding_category` (e.g. "missing security patch", "misconfigured service") | Enough for agency risk analysis |
| `tier_1_ref` (sha256) | Cryptographic link back to the unredacted source |

A finding in Tier 2 **does not** carry:

| Field | Rationale |
|---|---|
| Plugin IDs (Tenable, Qualys, OpenSCAP, …) | Maps directly to an exploit technique |
| CVE identifiers | Maps to published exploit code |
| Specific affected asset names / IPs / FQDNs | Reduces per-host targeting risk |
| Raw plugin output / payload strings | Contains the exploit path itself |
| Exploit availability / weaponization flags | Precisely the signal an attacker seeks |

The full allow / deny set lives in canon at `src/uiao/canon/redaction-profile.yaml`. Any field not explicitly named in the allow list is stripped by default (deny-by-default).

### D3. Remediation summary is truncated at 280 characters

Long-tail remediation narratives exceed the cap; the redactor truncates at 280 chars and appends `… [truncated — see tier_1_ref]`. Findings whose full remediation text matters to an agency customer require the 3PAO/FedRAMP reviewer to resolve the `tier_1_ref` back to the unredacted source.

### D4. Redaction is a pipeline stage, not an adapter concern

Redaction happens in `scripts/conmon/redact.py`, which runs **after** adapter normalization and **before** the E5 `distribute.py` step. Adapters continue to emit full-fidelity normalized findings; the normalizer doesn't know or care that distribution is happening. This preserves the current adapter contract and keeps redaction logic centralized — one module to audit, one test suite to write.

### D5. Tier-1 access control

Tier-1 (unredacted) artifacts under `evidence/raw/**` are protected by CODEOWNERS + branch protection. Concrete posture:

- CODEOWNERS assigns `evidence/raw/**` to a dedicated `@WhalerMike/3pao-review` team (or equivalent) — only members of that team can merge changes to that path.
- Branch protection on `main` requires CODEOWNERS review on touches to `evidence/raw/**`.

This is the **lightweight** option among the three reviewed in the draft (CODEOWNERS + branch protection | access-controlled bucket | cryptographic separation). Promotion to a stronger posture is tracked in the Promotion Checklist below and would be its own ADR amendment.

### D6. Redaction profile is a versioned canon artifact

`src/uiao/canon/redaction-profile.yaml` pins D2's allow / deny lists as canon. Changing the profile requires an **ADR amendment** (not just a registry PR). This prevents well-intentioned-but-wrong edits from quietly re-exposing exploit detail — the redaction profile is the *control*, not just a config file.

### D7. Alignment with VDR-RPT-NID

When the VDR Balance Improvement Release publishes (Notice 0009 deadline 2027-06-01), UIAO **retains ADR-045 as a supplemental policy above VDR-RPT-NID's floor**. The profile is designed to be *strictly more conservative* than VDR-RPT-NID is expected to require, so retaining it tightens UIAO's posture faster than any upstream change. A future retirement ADR supersedes ADR-045 only if VDR-RPT-NID introduces a profile that is equivalent-or-stricter — until then, ADR-045 is authoritative for UIAO's redaction floor.

### D8. Class-differentiated profiles are a future-proof hook

The redaction profile at launch applies uniformly. The E5 agency-customer-registry includes `data-classification: moderate | high` per agency, anticipating a future split where FedRAMP-High customers may receive a less-redacted subset than FedRAMP-Moderate. D8 is a *hook*, not a commitment — day one, both Moderate and High receive the same Tier-2 redaction; any differential unlocks via a subsequent ADR after operational signal.

## Consequences

### Positive

- UIAO has a defensible answer to the CSP-AB / cb-axon thread in community #130: "here's what we strip, here's what we keep, here's the audit trail."
- Shipping E5 can proceed without accumulating an unredacted-distribution debt.
- The redaction profile is a canonical artifact, so a 3PAO review has exactly one file to read to understand what an agency customer sees.
- Tier-1 retention keeps full fidelity for corrective-action or FedRAMP investigation.
- D7's supplemental posture makes VDR BIR migration *additive* rather than disruptive.

### Negative / deferred

- **N1. The 280-char remediation summary cap is editorial.** Some findings have legitimately long-tail explanations that don't fit. The redactor appends a truncation marker + `tier_1_ref`; the contract is "Tier-2 consumers who need the full text resolve it via their 3PAO access." If this proves too narrow in practice, the cap is a profile-level tunable (profile amendment required).
- **N2. Tier-1 access control is environmental, not cryptographic.** D5 uses CODEOWNERS + branch protection — a repo-layer guard, not a mathematical one. Cryptographic tier separation (encrypt Tier-1, give the key only to 3PAOs) is a Promotion-Checklist follow-up ADR, not scoped here.
- **N3. Some adapters don't emit plugin IDs or CVEs today** (configuration scanners, for example). For those, the redaction step is close to a no-op. The profile is still applied for consistency, but most of the action happens for vulnerability scanners.
- **N4. Upstream change risk.** If FedRAMP ratifies RFC-0026 with explicit language on raw scan distribution, UIAO's profile may need to tighten OR loosen. The profile is designed to tighten gracefully; loosening would require a new ADR.

## Alternatives considered

- **Ship E5 without redaction, tighten later.** Rejected — unredacted distribution is the exact failure mode CSP-AB et al. flagged, and "we'll clean it up in v2" is not a defensible audit answer.
- **Redact at the adapter layer.** Rejected — couples redaction policy to every adapter's implementation; the same finding would need to be redacted differently depending on whether it's for 3PAO or agency consumption. Central policy with a pipeline stage wins.
- **Use scanner-native redaction (e.g. Tenable's report templates).** Rejected — the profile is canon; enforcement cannot rely on a third-party tool's opinion of what's sensitive.
- **Defer this ADR until FedRAMP's final RFC-0026 language is known.** Rejected — E5 depends on this, and E5's enforcement-clock target is 2026-11-30. Better to ship a conservative profile now and tighten post-ratification than to ship unredacted.
- **Go with the stronger Tier-1 access model (cryptographic or access-controlled bucket) day one.** Rejected for initial ship — added complexity without a concrete 3PAO requirement for that posture today. D5's CODEOWNERS path is the explicit minimum viable guard; promotion is a focused follow-up ADR.

## Promotion checklist

Before this ADR can move from `PROPOSED` to `Accepted`:

- [ ] `src/uiao/canon/redaction-profile.yaml` committed and CI-validated.
- [ ] `scripts/conmon/redact.py` committed with complete test coverage (positive, negative, truncation, tier-1-ref stability, profile-driven behavior).
- [ ] First real scan run exercises the pipeline end-to-end in a non-production environment.
- [ ] CODEOWNERS entry for `evidence/raw/**` is active with a named 3PAO review team.
- [ ] UIAO_132 §2.3 updated to reference ADR-045 as the disclosure control for RV5-CA07-VLN Pathway-2.
- [ ] Decide whether to promote Tier-1 access from CODEOWNERS to access-controlled bucket or cryptographic separation (can be post-acceptance; a later ADR amendment).

## Related work

- [ADR-025](adr-025-continuous-monitoring-program-and-customer-docs-platform.md) — Continuous Monitoring Program architecture.
- [ADR-043](adr-043-fedramp-rfc-0026-ca7-integration.md) — RFC-0026 CA-7 integration + Pathway-2 posture (D1, D2).
- `UIAO_132` — FedRAMP RFC-0026 CA-7 Pathway Integration (operational companion to ADR-043).
- `docs/docs/uiao-rfc-0026-roadmap.md` — RFC-0026 enhancement roadmap § E7.
- FedRAMP community discussion [#130](https://github.com/FedRAMP/community/discussions/130) — the RFC comment thread that surfaced the disclosure asymmetry.

## Change log

| Version | Date | Change | Author |
|---|---|---|---|
| 0.1-DRAFT | 2026-04-23 | Initial draft under `docs/docs/` pending review | Automation |
| 1.0-PROPOSED | 2026-04-23 | Promoted to canon (this file) after all 4 review questions resolved to recommended defaults | WhalerMike |
