# UIAO Compliance Dashboard

## Overall Compliance Posture
- Status: **Moderate Risk**
- Controls Evaluated: 10
- PASS: 9
- WARN: 1
- FAIL: 0

---

## Control Status Summary

| Control | Status | Evidence | Severity |
|--------|--------|----------|----------|
| IA-2 | PASS | MFAEnabled=true | Low |
| AC-17 | PASS | LegacyAuthEnabled=false | Low |
| AC-2(1) | PASS | AdminCount=4 | Low |
| AC-21 | WARN | ExternalSharingEnabled=true | Medium |
| SI-3 | PASS | SafeLinksEnabled=true | Low |
| SI-3 | PASS | SafeAttachmentsEnabled=true | Low |
| AU-2 | PASS | MailboxAuditingEnabled=true | Low |
| SC-7 | PASS | ExternalForwardingAllowed=false | Low |
| AC-17 | PASS | ConditionalAccessPoliciesCount=3 | Low |
| SC-28 | PASS | DLPPoliciesCount=2 | Low |

---

## Drift Summary
- Drift Detected: **Yes**
- Affected Controls: AC-21
- POA&M Entries: 1

---

## Evidence Summary
- Evidence Objects: 10
- Provenance Manifests: 1
- Hash Integrity: 100%

---

## OSCAL Outputs
- SSP: ✔
- SAP: ✔
- SAR: ✔
- POA&M: ✔

---

## Enforcement Summary
- Conditional Access Policies: 3
- Enforcement Adapter Status: Operational

---

## POA&M Summary

| Weakness | Control | Severity | Status |
|----------|---------|----------|--------|
| External Sharing Enabled | AC-21 | Medium | Open |

---

## Last Assessment
- Run Date: 2026-04-10
- Source: SCuBA / ScubaGear
- Tenant: UIAO Assessment Tenant
- Pipeline: UIAO SCuBA Adapter v1.0
