# Draft — Feedback to OMB OFCIO on the 2025 Federal AI Use Case Inventory

**To:** OFCIO_AI@omb.eop.gov
**Subject:** Feedback on the 2025 Federal AI Use Case Inventory — Identity Governance Gap and a Proposed Schema Extension
**From:** Michael Stratton, [Agency/Organization]

---

Thank you for publishing the 2025 Federal AI Use Case Inventory in machine-readable format. The transparency it provides is genuinely useful, and the field structure of the data dictionary — particularly the `have_ato`, `has_pii`, and `hi_*` governance checklist fields — reflects careful thinking about AI accountability.

I am writing to share a specific gap I identified in the inventory schema and to offer a concrete proposal to address it in the 2026 edition.

## The Identity Governance Gap

The current inventory schema has no fields for identity governance: who owns the service account or workload identity the AI system operates under, what credential tier it uses, whether that credential is subject to rotation policy, and what organizational unit in the federal hierarchy holds ownership responsibility.

This absence matters operationally. A deployed AI system has an Authorization to Operate (`have_ato = Yes`) — but the ATO governs the system as a technology artifact. It does not govern the identity the system operates under once deployed. That identity — the service account, the managed identity, the API credential — is the actual access surface. It can be compromised, over-permissioned, or orphaned (surviving the system that created it) without any of the inventory's current fields detecting the condition.

The 90 agentic AI systems in the 2025 inventory make this gap urgent. An agentic system acts continuously and autonomously inside the same identity substrate as human users. Its credential does not sit idle between login attempts. If it is unowned, unrotated, or over-permissioned, it is an ungoverned actor inside the federal identity environment — not a theoretical risk, an operational one.

## A Proposed Field Extension for 2026

I propose four new fields for the 2026 inventory schema. All four are derivable from information agencies already hold at deployment time:

| Field name | Description | Type |
|---|---|---|
| `identity_type` | Type of identity the system operates under: `managed-identity`, `service-account`, `workload-identity-federation`, `api-key`, `none`, `unknown` | multiple choice |
| `owning_org_unit` | The organizational unit (bureau, office, or division) that holds ownership responsibility for the credential | free text |
| `credential_rotation_policy` | Whether the credential is subject to a documented rotation policy: `yes`, `no`, `not-applicable` | multiple choice |
| `identity_governance_system` | The identity management system that tracks the credential, if any: e.g. system name, or `none` | free text |

These four fields do not impose a new compliance burden. They ask agencies to record what should already be documented in their deployment artifacts. Agencies that cannot answer these fields for a deployed system have identified an identity governance gap in their own environment — which is precisely what the inventory is designed to surface.

## Connection to Existing Federal Standards

These fields align directly with:

- **NIST SP 800-53 Rev 5 IA-2, IA-4, AC-2** — identification, authenticator management, and account management controls that apply to non-human identities
- **CISA Zero Trust Maturity Model, Identity Pillar** — service accounts and workload identities are explicitly in scope
- **OMB M-22-09 (Zero Trust Strategy)** — requires agencies to inventory and govern non-human identities as part of the zero trust transition

The M-25-21 AI governance framework and the zero trust identity mandate address the same population from different angles. The inventory schema extension proposed here would make them mutually reinforcing.

## A Possible Governance Model

The organizational placement field (`owning_org_unit`) enables a governance chain that the current inventory cannot support: connecting the AI system to the bureau hierarchy that deployed it, then applying the bureau's existing identity governance processes to the AI system's credential.

Federal agencies that have implemented organizational-hierarchy-aware identity governance (OrgPath-style systems that derive policy from organizational position rather than manually maintained lists) can apply rotation policy, access review, and deprovisioning to AI systems through the same mechanism they use for human accounts — if the organizational placement is on record.

Without the placement, the AI identity surface is invisible to every governance process that relies on knowing where in the organization a system belongs.

I would welcome the opportunity to discuss this proposal further, share a reference schema, or contribute to the development of the 2026 inventory data dictionary. I can be reached at michael.francis.stratton@gmail.com.

---

*Attachment available on request: UIAO_196 AI System Identity Record schema specification, including field mappings from the 2025 OMB inventory to the proposed 2026 extension fields.*
