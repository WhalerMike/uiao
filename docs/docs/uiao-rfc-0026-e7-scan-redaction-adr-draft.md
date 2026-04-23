# E7 Draft ADR — Scan Artifact Redaction Policy for Multi-Agency Distribution

**Proposed ADR number:** ADR-045 (next free)
**Status:** **DRAFT — awaiting review; not yet canon**
**Date:** 2026-04-23
**Roadmap entry:** [`docs/docs/uiao-rfc-0026-roadmap.md`](uiao-rfc-0026-roadmap.md) § E7
**Extends:** ADR-025, ADR-043

> When approved, this document moves to `src/uiao/canon/adr/adr-045-scan-redaction-policy.md` and the status promotes from DRAFT → PROPOSED. This copy is deliberately kept outside `canon/` to avoid accidentally taking canonical effect before review.

---

## Context

### The disclosure asymmetry

RFC-0026 RV5-CA07-VLN's Pathway-2 deliverable list includes **monthly OS / DB / web app / container / service configuration scans shared with agency customers**. The most-upvoted thread in FedRAMP community discussion #130 — CSP-AB, cb-axon, judgecspab-max, rgaffey, mjprager — flagged that this requirement, as written, is:

1. **Operationally impractical** — in an IaaS-scale tenant, raw scan output runs to terabytes per month
2. **Actively dangerous** — distributing unredacted exploit-path detail to every agency customer broadens the attack surface: each receiving agency's ingest pipeline becomes a target worth compromising for the exploit intelligence alone
3. **Internally inconsistent** — the modernized pathway's VDR Balance Improvement Release explicitly prohibits irresponsible vulnerability disclosure, yet the traditional pathway currently imposes no such guardrail

UIAO runs Pathway-2 per ADR-043 D1 and therefore inherits the distribution requirement. UIAO_132 §2.3 is silent on how raw scan content should be handled before agency hand-off.

### Where UIAO stands today

- `vulnscan_adapter.py` + `vulnscan_parser.py` normalize raw scanner output into UIAO's canonical finding shape
- `conmon-aggregate.yml` rolls findings into the monthly POA&M CSV and OSCAL drop
- The E5 registry (pending) will fan that rollup out to each agency customer on their declared delivery channel
- **Nothing in the pipeline today distinguishes between "3PAO-grade evidence" and "agency-grade evidence"** — whatever the normalizer produces is what every consumer sees

### Why this ADR now

The E5 distribution layer is the point at which redaction decisions become enforceable. Shipping E5 without a redaction policy means UIAO's first monthly distribution ships unredacted exploit-path detail to multiple agencies — exactly what CSP-AB et al. argued against.

## Decision

### D1. Two-tier evidence storage

Every scan artifact is stored in exactly one of two tiers:

- **Tier 1 — Unredacted (3PAO + FedRAMP corrective-action only).** Raw scanner output, plugin identifiers, CVE-to-asset mappings, and exploit-path payloads. Lives under `evidence/raw/<adapter-id>/<yyyy-mm>/`. Access restricted at the repository layer (CODEOWNERS + protected branch, or a separate restricted-access bucket when the evidence moves off-repo).
- **Tier 2 — Redacted (agency distribution surface).** The same findings with the sensitive fields stripped per the profile below. Lives under `evidence/distribution/<agency-id>/<yyyy-mm>/` — the same location E5 writes receipts to.

Every Tier-2 artifact carries a cryptographic back-reference to its Tier-1 source (sha256 of the raw finding), so 3PAOs and FedRAMP reviewers who *do* have Tier-1 access can trace any redacted finding back to the original without the redacted file leaking the payload.

### D2. Redaction profile

A finding in Tier 2 retains:

| Field | Rationale |
|---|---|
| CSP-assigned tracking ID | Primary key for ConMon correlation |
| Risk level (critical / high / moderate / low) | Agency SLA trigger |
| Finding state (open / closed / deferred / accepted) | POA&M state machine |
| Affected control family (AC / AU / SC / …) | SSP cross-reference |
| First observed, last observed timestamps | Timeliness SLA (ADR-043 D2) |
| Remediation plan summary (≤ 280 chars, no identifiers) | Agency visibility into CSP posture |
| Planned completion date | POA&M CSV column |
| Finding *category* (e.g. "missing security patch", "misconfigured service") | Enough for agency risk analysis |

A finding in Tier 2 **does not** carry:

| Field | Rationale |
|---|---|
| Plugin IDs (Tenable, Qualys, OpenSCAP…) | Maps directly to an exploit technique |
| CVE identifiers | Maps to published exploit code |
| Specific affected asset names / IPs / FQDNs | Reduces per-host targeting risk |
| Raw plugin output / payload strings | Contains the exploit path itself |
| Exploit availability / weaponization flags | Precisely the signal an attacker seeks |

### D3. Redaction is a pipeline stage, not an adapter concern

Redaction happens in a new `scripts/conmon/redact.py` step that runs **after** adapter normalization and **before** the E5 distribute.py step. Adapters continue to emit full-fidelity normalized findings; the normalizer doesn't know or care that distribution is happening. This preserves the current adapter contract and keeps redaction logic centralized (one module to audit, one test suite to write).

### D4. Redaction policy is a versioned canon artifact

`src/uiao/canon/redaction-profile.yaml` pins the field allow/deny lists above as canon. Changing the profile requires an ADR amendment (not just a registry PR). This prevents well-intentioned-but-wrong edits from quietly re-exposing exploit detail — the redaction profile is the control, not just a config file.

### D5. Alignment with VDR-RPT-NID

The VDR Balance Improvement Release (once published) includes a Responsible Disclosure principle for non-sensitive-information (NID) reporting. UIAO's redaction profile is designed to be the Pathway-2 equivalent of VDR-RPT-NID: when Pathway-1 migration happens (2027-06-01 per Notice 0009, per E8), the redaction profile is the cleanest artifact to map into the BIR's disclosure surface.

### D6. Class-differentiated profiles (future-proof hook)

The redaction profile at launch applies uniformly. The registry design in E5 includes `data-classification: moderate | high` per agency, anticipating a future split where FedRAMP-High customers may receive a less-redacted subset than FedRAMP-Moderate. D6 is a *hook*, not a commitment — day one, both Moderate and High receive the same Tier-2 redaction; any differential unlocks via a subsequent ADR after operational signal.

## Consequences

### Positive

- UIAO has a defensible answer to the CSP-AB / cb-axon thread in community #130: "here's what we strip, here's what we keep, here's the audit trail"
- Shipping E5 can proceed without accumulating an unredacted-distribution debt
- The redaction profile is a canonical artifact, so a 3PAO review has exactly one file to read to understand what an agency customer sees
- Tier-1 retention keeps full fidelity for corrective-action or FedRAMP investigation

### Negative / deferred

- **N1. The "remediation plan summary ≤ 280 chars" constraint is editorial.** Some findings have legitimately long-tail explanations that don't fit. The script will need a truncation + linking strategy; this ADR punts on the exact format.
- **N2. Tier-1 access control is environmental, not cryptographic.** This ADR assumes CODEOWNERS + branch protection or a separate restricted bucket. Cryptographic tier separation (encrypt Tier-1, give the key only to 3PAOs) is a follow-up ADR — not scoped here.
- **N3. Some adapters don't emit plugin IDs or CVEs today** (configuration scanners, for example). For those, the redaction step is close to a no-op. The profile is still applied for consistency, but most of the action happens for vuln scanners.
- **N4. Upstream change risk.** If FedRAMP ratifies RFC-0026 with explicit language on raw scan distribution, UIAO's profile may need to tighten OR loosen. The profile is designed to tighten gracefully; loosening would require a new ADR.

## Alternatives considered

- **Ship E5 without redaction, tighten later.** Rejected — unredacted distribution is the exact failure mode CSP-AB et al. flagged, and *"we'll clean it up in v2"* is not a defensible audit answer.
- **Redact at the adapter layer.** Rejected — couples redaction policy to every adapter's implementation; the same finding would need to be redacted differently depending on whether it's for 3PAO or agency consumption. Central policy with a pipeline stage wins.
- **Use scanner-native redaction (e.g. Tenable's report templates).** Rejected — the profile is canon; enforcement cannot rely on a third-party tool's opinion of what's sensitive.
- **Defer this ADR until FedRAMP's final RFC-0026 language is known.** Rejected — E5 depends on this, and E5's enforcement-clock target is 2026-11-30. Better to ship a conservative profile now and tighten post-ratification than to ship unredacted.

## Promotion checklist

Before this draft can promote to `src/uiao/canon/adr/adr-045-scan-redaction-policy.md` with `status: PROPOSED`:

- [ ] User has reviewed D1–D6 and confirmed the redaction profile's included / excluded fields match their risk model
- [ ] User has decided on Tier-1 access control (CODEOWNERS + branch protection vs. separate restricted bucket vs. cryptographic)
- [ ] The ADR number (ADR-045 here) is still the next free slot (check `ls src/uiao/canon/adr/`)
- [ ] `redaction-profile.yaml` is drafted as the companion canon artifact
- [ ] `scripts/conmon/redact.py` has a design sketch (can be a separate follow-up ADR or a design memo)

---

## Open questions for the user

1. **Field list tuning.** Is anything in the "retained" list you'd rather strip (e.g. finding-category strings that might reveal a vendor stack), or anything in the "stripped" list you'd rather keep (e.g. CVE IDs because some agencies specifically ask for them)?
2. **Tier-1 access model.** CODEOWNERS + branch protection is the lightweight option; a separate restricted bucket (GitHub Releases + access control, or an S3 bucket with IAM) is the stronger option. Your preference?
3. **"Remediation plan summary" length.** 280 chars is a guess. Is there a ConMon-template column length that makes more sense?
4. **Pathway-1 readiness.** When the VDR BIR publishes (2027-06-01 deadline), do you want this ADR to auto-retire in favor of VDR-RPT-NID, or do you want UIAO to maintain the profile as a supplemental policy above VDR's floor?

---

## Change log

| Version | Date | Change | Author |
|---|---|---|---|
| 0.1-DRAFT | 2026-04-23 | Initial drafting as review-only memo under `docs/docs/`; promotes to `canon/adr/adr-045-*.md` on approval | Automation |
