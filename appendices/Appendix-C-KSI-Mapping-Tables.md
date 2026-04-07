# Appendix C — KSI Mapping Tables

## SCuBA → KSI → Control Mapping

| SCuBA Field | KSI | NIST 800-53 | FedRAMP | CISA SCuBA | Status Logic |
|---|---|---|---|---|---|
| MFAEnabled | KSI-001 | IA-2, IA-2(1), IA-2(11) | IA-2, IA-2(1) | M365-ACCT-001 | true = PASS |
| LegacyAuthEnabled | KSI-002 | AC-17, IA-5 | AC-17(2) | M365-AUTH-002 | false = PASS |
| AdminCount | KSI-003 | AC-2(1), AC-6 | AC-2(1) | M365-PRIV-003 | <= 5 = PASS |
| ExternalForwardingAllowed | KSI-004 | SC-7, SC-8 | SC-7(3) | M365-EXO-004 | false = PASS |
| MailboxAuditingEnabled | KSI-005 | AU-2, AU-12 | AU-2, AU-12 | M365-EXO-005 | true = PASS |
| ExternalSharingEnabled | KSI-006 | AC-3, AC-21 | AC-21 | M365-SPO-006 | false = PASS |
| SafeLinksEnabled | KSI-007 | SI-3, SI-4 | SI-3 | M365-ATP-007 | true = PASS |
| SafeAttachmentsEnabled | KSI-008 | SI-3, SI-4 | SI-3 | M365-ATP-008 | true = PASS |
| ConditionalAccessPolicies | KSI-009 | AC-3, AC-17 | AC-17 | M365-CA-009 | count >= 1 = PASS |
| DLPPolicies | KSI-010 | MP-4, SC-28 | SC-28 | M365-DLP-010 | count >= 1 = PASS |

## Severity Model

| Status | Meaning |
|---|---|
| PASS | Control satisfied |
| WARN | Control partially satisfied or requires review |
| FAIL | Control not satisfied |
| CRITICAL | Critical risk — immediate remediation required |

## Provenance

- KSI Ruleset Version: 1.0
- Adapter Version: 1.0
- Source: uiao-core/ksi/rules/
