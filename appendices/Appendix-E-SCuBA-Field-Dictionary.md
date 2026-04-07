# Appendix E — SCuBA Field Dictionary

## E.1 Purpose

This appendix is the canonical human-readable reference for all fields in the UIAO normalized SCuBA schema. It maps every field to its source, type, KSI rule, and governance notes.

The machine-readable schema is at:
`uiao-core/adapters/scuba/schemas/scuba-normalized.schema.json`

---

## E.2 Assessment Metadata Fields

These fields capture run-level metadata about the SCuBA assessment execution.

| Field | Type | Source | Description | Required |
|---|---|---|---|---|
| `assessment_date` | string (date-time) | ScubaGear output | ISO 8601 timestamp of the SCuBA assessment run | Yes |
| `tool_version` | string | ScubaGear output | Version of the ScubaGear tool used | Yes |
| `collector_host` | string | Environment | Hostname of the machine that ran SCuBA | Yes |
| `collector_user` | string | Environment | Account that executed the SCuBA run | Yes |
| `run_id` | string | UIAO adapter | Unique run identifier (format: scuba-run-YYYYMMDD-HHmmss) | Yes |

---

## E.3 Tenant Fields

These fields identify the Microsoft 365 tenant assessed.

| Field | Type | Source | Description | Required |
|---|---|---|---|---|
| `tenant_id` | string | ScubaGear output | Azure AD / Entra ID tenant GUID | Yes |
| `subscription_id` | string | ScubaGear output | Azure subscription ID (if applicable) | No |

---

## E.4 Raw Artifact Reference Fields

These fields record the filenames of the raw SCuBA output artifacts.

| Field | Type | Source | Description | Required |
|---|---|---|---|---|
| `results_file` | string | UIAO adapter | Filename of the raw ScubaGear results JSON | No |
| `settings_export_file` | string | ScubaGear output | Filename of the settings export JSON | No |
| `action_plan_file` | string | ScubaGear output | Filename of the action plan CSV | No |

---

## E.5 Normalized Fields

These are the core security configuration fields extracted and normalized from ScubaGear output. Each maps to one or more KSI rules.

| Field | Type | KSI | NIST 800-53 | FedRAMP | Description |
|---|---|---|---|---|---|
| `MFAEnabled` | boolean | KSI-001 | IA-2, IA-2(1) | IA-2 | Whether MFA is enforced for all accounts. `true` = PASS. |
| `LegacyAuthEnabled` | boolean | KSI-002 | AC-17, IA-5 | AC-17(2) | Whether legacy authentication protocols are enabled. `false` = PASS. |
| `AdminCount` | integer | KSI-003 | AC-2(1), AC-6 | AC-2(1) | Number of global administrators. <= 5 = PASS. |
| `ExternalForwardingAllowed` | boolean | KSI-004 | SC-7, SC-8 | SC-7(3) | Whether automatic external email forwarding is allowed. `false` = PASS. |
| `MailboxAuditingEnabled` | boolean | KSI-005 | AU-2, AU-12 | AU-2, AU-12 | Whether mailbox auditing is enabled for all users. `true` = PASS. |
| `ExternalSharingEnabled` | boolean | KSI-006 | AC-3, AC-21 | AC-21 | Whether external sharing is enabled in SharePoint/OneDrive. `false` = PASS; `true` = WARN. |
| `SafeLinksEnabled` | boolean | KSI-007 | SI-3, SI-4 | SI-3 | Whether Microsoft Defender Safe Links is enabled. `true` = PASS. |
| `SafeAttachmentsEnabled` | boolean | KSI-008 | SI-3, SI-4 | SI-3 | Whether Microsoft Defender Safe Attachments is enabled. `true` = PASS. |
| `ConditionalAccessPoliciesCount` | integer | KSI-009 | AC-3, AC-17 | AC-17 | Number of active Conditional Access policies. >= 1 = PASS. |
| `DLPPoliciesCount` | integer | KSI-010 | MP-4, SC-28 | SC-28 | Number of active Data Loss Prevention policies. >= 1 = PASS; 0 = WARN. |

---

## E.6 KSI Result Fields

These fields are produced by the KSI evaluation engine and appended to the normalized document.

| Field | Type | Values | Description |
|---|---|---|---|
| `ksi_id` | string | KSI-001 … KSI-010 | Unique KSI rule identifier |
| `status` | string | PASS, WARN, FAIL | Evaluation result |
| `severity` | string | Low, Medium, High, Critical | Risk severity for this result |
| `details` | string | Free text | Human-readable explanation of the result |

---

## E.7 Status and Severity Definitions

| Status | Meaning |
|---|---|
| PASS | Control is satisfied |
| WARN | Control requires review or is partially satisfied |
| FAIL | Control is not satisfied |

| Severity | Meaning |
|---|---|
| Low | Informational — no immediate action required |
| Medium | Should be addressed in next governance cycle |
| High | Should be remediated promptly |
| Critical | Immediate remediation required |

---

## E.8 Schema Governance

- Schema version: 1.0
- Schema location: `uiao-core/adapters/scuba/schemas/scuba-normalized.schema.json`
- Changes to this schema require an ADR (see [Appendix D](Appendix-D-ADR-Index.md))
- `additionalProperties: true` is set to allow forward compatibility as ScubaGear evolves

---

## E.9 Related Documents

- [Appendix B — UIAO SCuBA Pipeline](Appendix-B-UIAO-SCuBA-Pipeline.md)
- [Appendix C — KSI Mapping Tables](Appendix-C-KSI-Mapping-Tables.md)
- [Appendix D — ADR Index](Appendix-D-ADR-Index.md)
- [SCuBA Pipeline Runbook](../docs/SCuBA-Pipeline-Runbook.md)
