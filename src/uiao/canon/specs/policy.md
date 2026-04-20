---
document_id: UIAO_116
title: "UIAO Enforcement Policy Language (EPL)"
version: "1.0"
status: Current
classification: CANONICAL
owner: "Michael Stratton"
created_at: "2026-04-14"
updated_at: "2026-04-14"
boundary: "GCC-Moderate"
---

# UIAO Enforcement Policy Language (EPL)

EPL is a declarative language for expressing enforcement requirements within the UIAO compliance engine.

---

## Purpose

EPL allows UIAO operators to:
- Define enforcement rules tied to specific NIST controls
- Express conditions under which enforcement actions are triggered
- Link enforcement actions to evidence collection
- Automatically generate findings and POA&M entries when conditions are violated

---

## Syntax

```
policy <name> {
  control "<control-id>"
  when "<condition>"
  enforce "<action>"
  evidence "<evidence-type>"
}
```

---

## Fields

| Field | Description |
|-------|-------------|
| policy | The policy name (unique identifier) |
| control | The NIST 800-53 control ID this policy enforces |
| when | The condition expression that triggers enforcement |
| enforce | The enforcement adapter action to call |
| evidence | The evidence field to collect after enforcement |

---

## Example: Enforce MFA

```
policy enforce_mfa {
  control "IA-2"
  when "MFAEnabled == false"
  enforce "conditional_access.enable('mfa_policy')"
  evidence "MFAEnabled"
}
```

---

## Example: Disable Legacy Auth

```
policy disable_legacy_auth {
  control "AC-17"
  when "LegacyAuthEnabled == true"
  enforce "conditional_access.disable('legacy_auth_policy')"
  evidence "LegacyAuthEnabled"
}
```

---

## Example: Restrict External Sharing

```
policy restrict_external_sharing {
  control "AC-21"
  when "ExternalSharingEnabled == true"
  enforce "sharepoint.restrict_external_sharing()"
  evidence "ExternalSharingEnabled"
}
```

---

## Execution Model

1. UIAO evaluates the condition against normalized SCuBA evidence
2. If the condition is true (violation detected):
   a. A finding is generated and recorded
   b. The enforcement adapter action is called
   c. Evidence is collected post-enforcement
   d. A POA&M entry is created if enforcement fails
   e. The OSCAL SAR is updated with the finding
3. If the condition is false (compliant):
   a. The control is marked as satisfied
   b. Evidence is recorded
   c. The OSCAL SSP is updated

---

## Supported Condition Operators

| Operator | Description | Example |
|----------|-------------|---------|
| == | Equals | MFAEnabled == true |
| != | Not equals | AdminCount != 0 |
| > | Greater than | AdminCount > 5 |
| < | Less than | PolicyCount < 1 |
| >= | Greater than or equal | PolicyCount >= 3 |
| <= | Less than or equal | PolicyCount <= 10 |

---

## Supported Enforcement Adapters

| Adapter | Description |
|---------|-------------|
| conditional_access | Azure AD Conditional Access policies |
| sharepoint | SharePoint Online configuration |
| exchange | Exchange Online configuration |
| defender | Microsoft Defender for Office 365 |
| dlp | Microsoft Purview DLP policies |

---

## File Location

EPL policy files are stored in:

```
uiao/policy/
  ├── EPL-Specification.md   (this file)
  ├── enforce-mfa.epl
  ├── disable-legacy-auth.epl
  ├── restrict-external-sharing.epl
  └── require-safe-links.epl
```
