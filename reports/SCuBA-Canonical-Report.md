# UIAO SCuBA Canonical Report

**Report ID:** SCUBA-RPT-2026-04-07-01
**Version:** 1.0
**Date:** 2026-04-07
**Tenant:** 00000000-0000-0000-0000-000000000000

---

## 1. Executive Summary

This report documents the results of a SCuBA (ScubaGear) assessment executed through the UIAO governance fabric. The tenant demonstrates strong identity posture, modern authentication enforcement, and robust threat protection. The only moderate-risk area is external sharing, which remains enabled and requires governance review.

**Overall Posture:** Strong
**PASS:** 9
**WARN:** 1
**FAIL:** 0

---

## 2. Assessment Metadata

| Field | Value |
|---|---|
| Assessment Date | 2026-04-07T03:00:00Z |
| Tool Version | ScubaGear 1.2.0 |
| Collector Host | SCUBA-SRV-01 |
| Collector User | svc_scuba |
| Run ID | scuba-run-20260407-030000 |

---

## 3. SCuBA Results Overview

- **Total KSIs evaluated:** 10
- **PASS:** 9
- **WARN:** 1
- **FAIL:** 0

Primary strengths:
- MFA enforced
- Legacy authentication disabled
- Conditional Access configured
- Safe Links and Safe Attachments enabled

Primary concern:
- External sharing enabled (requires governance review)

---

## 4. KSI Evaluation Summary

| KSI ID | Description | Status | Severity |
|---|---|---|---|
| KSI-001 | Multi-Factor Authentication | PASS | Low |
| KSI-002 | Legacy Authentication Disabled | PASS | Low |
| KSI-003 | Global Administrator Count | PASS | Low |
| KSI-004 | External Forwarding Restrictions | PASS | Low |
| KSI-005 | Mailbox Auditing Enabled | PASS | Low |
| KSI-006 | External Sharing Restrictions | WARN | Medium |
| KSI-007 | Safe Links Protection | PASS | Low |
| KSI-008 | Safe Attachments Protection | PASS | Low |
| KSI-009 | Conditional Access Enforcement | PASS | Low |
| KSI-010 | Data Loss Prevention Enforcement | PASS | Low |

---

## 5. Control Mapping Summary

| SCuBA Field | KSI | NIST 800-53 | FedRAMP | Status |
|---|---|---|---|---|
| MFAEnabled | KSI-001 | IA-2, IA-2(1), IA-2(11) | IA-2 | PASS |
| LegacyAuthEnabled | KSI-002 | AC-17, IA-5 | AC-17(2) | PASS |
| AdminCount | KSI-003 | AC-2(1), AC-6 | AC-2(1) | PASS |
| ExternalForwardingAllowed | KSI-004 | SC-7, SC-8 | SC-7(3) | PASS |
| MailboxAuditingEnabled | KSI-005 | AU-2, AU-12 | AU-2, AU-12 | PASS |
| ExternalSharingEnabled | KSI-006 | AC-3, AC-21 | AC-21 | WARN |
| SafeLinksEnabled | KSI-007 | SI-3, SI-4 | SI-3 | PASS |
| SafeAttachmentsEnabled | KSI-008 | SI-3, SI-4 | SI-3 | PASS |
| ConditionalAccessPolicies | KSI-009 | AC-3, AC-17 | AC-17 | PASS |
| DLPPolicies | KSI-010 | MP-4, SC-28 | SC-28 | PASS |

---

## 6. Detailed Findings

### Identity & Access
- **MFAEnabled:** true → PASS
- **LegacyAuthEnabled:** false → PASS
- **AdminCount:** 4 → PASS

### Messaging & Collaboration
- **ExternalForwardingAllowed:** false → PASS
- **MailboxAuditingEnabled:** true → PASS
- **ExternalSharingEnabled:** true → WARN

### Threat Protection
- **SafeLinksEnabled:** true → PASS
- **SafeAttachmentsEnabled:** true → PASS

### Governance
- **ConditionalAccessPoliciesCount:** 3 → PASS
- **DLPPoliciesCount:** 2 → PASS

---

## 7. Provenance

- Adapter Version: 1.0
- KSI Ruleset Version: 1.0
- Raw SCuBA Files:
  - ScubaResults_1234.json
  - ProvideSettingsExport.json
  - ActionPlan.csv
- Provenance Manifest ID: prov-scuba-20260407-01

All hashes, lineage, and environment details are recorded in the corresponding provenance manifest in uiao-core/provenance/manifests/.

---

## 8. Appendices

- Appendix A: Glossary
- Appendix B: UIAO SCuBA Pipeline
- Appendix C: KSI Mapping Tables
- Appendix D: ADR Index
- Appendix E: SCuBA Field Dictionary

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
