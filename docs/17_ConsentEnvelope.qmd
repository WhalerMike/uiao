---
title: "17 Consent Envelope"
author: "UIAO Modernization Program"
date: today
date-format: "MMMM D, YYYY"
format:
  html: default
  docx: default
  pdf: default
  gfm: default
---

# UIAO Federated Authorization & Consent Envelope

**Document:** 17
**Phase:** 5 — Data Governance Substrate
**Version:** 1.0
**Status:** Draft
**Classification:** CUI/FOUO
**Date:** 2026-04-01

---

## 1. Purpose

The UIAO Consent Envelope is the first machine-readable, purpose-bound, legally anchored consent model for inter-agency and federal-to-state canonical claim sharing. It operationalizes MOUs and legal authorities (including IRC § 6103, Privacy Act, and FISMA) into a computable, auditable envelope attached to every claim transmission.

---

## 2. Legal Authority Anchors

| Authority | Applicable Claim Domain | UIAO Enforcement |
|---|---|---|
| IRC § 6103 | Tax data (IRS → State) | `legal_authority` field; purpose-bound transmission only |
| Privacy Act (5 U.S.C. § 552a) | PII claims | Consent purpose and expiry enforced at adapter boundary |
| FISMA / FedRAMP | All federal cloud-transmitted claims | Adapter must hold active ATO |
| State Data Sharing Agreements | State-received federal claims | MOU reference required in envelope |

---

## 3. Consent Envelope Schema

```yaml
consent_envelope:
  envelope_id: "urn:uiao:consent:{uuid}"
  claim_id: "{urn:uiao:claim:...}"
  issuing_agency: "{agency_identifier}"
  receiving_agency: "{agency_identifier}"
  legal_authority: "{cite: e.g., IRC § 6103(d)}"
  purpose_code: "{ELIGIBILITY | BENEFITS | ENFORCEMENT | AUDIT | RESEARCH}"
  purpose_description: "{human-readable purpose statement}"
  consent_granted_by: "{individual_identity | agency_officer_identity}"
  consent_timestamp: "{ISO8601}"
  consent_expiry: "{ISO8601 or 'SESSION'}"
  permitted_uses:
    - use: "{use_code}"
      scope: "{AGENCY | PROGRAM | SYSTEM}"
  prohibited_uses:
    - "{SECONDARY_SALE | MARKETING | UNRESTRICTED_RESEARCH}"
  data_minimization: true | false
  cross_boundary_flag: true | false
  mou_reference: "{MOU_ID or null}"
  signature: "{agency officer mTLS thumbprint}"
```

---

## 4. Purpose Code Definitions

| Code | Description | Example |
|---|---|---|
| `ELIGIBILITY` | Determining benefit or program eligibility | SSA income verification for SNAP |
| `BENEFITS` | Active benefit administration | CMS claims processing |
| `ENFORCEMENT` | Law enforcement or compliance action | DHS immigration status verification |
| `AUDIT` | IG or compliance review | FedRAMP continuous monitoring |
| `RESEARCH` | Anonymized statistical research only | CDC disease surveillance |

---

## 5. Enforcement at the Adapter Boundary

- Every outbound claim transmission MUST carry a valid `consent_envelope`
- Adapters MUST validate `consent_expiry` before every transmission
- `prohibited_uses` violations MUST trigger a `P1-CRITICAL` drift event
- Cross-boundary transmissions (`cross_boundary_flag: true`) require Canon Steward countersignature

---

## 6. Compliance Mapping

| NIST Control | Consent Envelope Field |
|---|---|
| AC-4 (Information Flow) | `purpose_code`, `permitted_uses`, `prohibited_uses` |
| AC-22 (Publicly Accessible Content) | `consent_granted_by`, `data_minimization` |
| AR-4 (Privacy Monitoring) | `consent_expiry`, `cross_boundary_flag` |
| IP-1 (Consent) | Full envelope |

---

## 7. Cross-References

- `docs/15_ProvenanceProfile.md` — Provenance envelope that consent extends
- `docs/16_DriftDetectionStandard.md` — Authorization drift (DRIFT-AUTHZ) enforcement
- `docs/18_ClaimCatalog.md` — Claim records with `consent_required` flags
- `docs/19_ReconciliationModel.md` — Consent conflict resolution (CONFLICT-CONSENT)
- `docs/adapters/adapter-contract.md` — Adapter consent validation obligations

---

## 8. Revision History

| Version | Date | Author | Summary |
|---|---|---|---|
| 1.0 | 2026-04-01 | UIAO Canon Engine | Initial canonical release — Phase 5 Data Governance Substrate |
