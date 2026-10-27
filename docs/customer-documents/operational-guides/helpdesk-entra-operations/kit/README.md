# Help Desk / Cloud Services — Hybrid AD → Entra ID implementation kit (v1.6)

Vendor-neutral — only the platforms the agency already runs (Entra ID,
**ServiceNow**, SAM/SailPoint). **ServiceNow-first:** every request enters a
ServiceNow triage queue, is classified by required authority, and is routed to
the ServiceNow or SAM approval pipeline — executing automatically through the
**Microsoft Entra ID Spoke** where the spoke documents the action, and falling to
a manual Help Desk task for the gaps. Before any password, MFA or Temporary
Access Pass action the technician **verifies the person**; approval alone is not
enough.

## Contents

| Path | What it is |
|---|---|
| `documents/Helpdesk-Flow.docx` | **Start here.** Intake → triage → routing: the recommendation, the Entra ID Spoke capability crosswalk, the email-to-pipeline mechanisms, and **blueprint diagrams**. Includes ServiceNow + Microsoft references. |
| `documents/Help-Desk-Administrative-Responsibilities-Guide.docx` | Operations reference — authority boundaries, identity verification, the PAG / PIM eligible-not-active model, the SAM/ServiceNow/Entra three-platform workflow, Temporary Access Pass recovery, per-task procedures (with diagrams). |
| `documents/Enterprise-Application-Access-Governance-and-Approval-Model.docx` | Governing policy — risk-tiered approval chains, RACI, application ownership, group-based access, the three approval workflows (with diagrams). |
| `documents/Governance-Structure-Brief.docx` | The four-layer governance/ownership design concept underneath both (with diagram). |
| `implementation-path.md` | The operating model + the Task Authority & Routing Matrix (with the `Execution` and `Verification` columns) + the four implementation layers + run order. |
| `CHANGELOG.md` | What changed in each kit release. |
| `lib/HelpDeskEntra.psm1` | Shared module — the **routing matrix as data** (`$RequestRoutingTable`), Connect helper and scope sets, critical-permission risk list, logging. **Extend the matrix here.** |
| `scripts/Invoke-RequestTriage.ps1` | Email triage classifier — reads the shared mailbox's Inbox, classifies by authority, routes to ServiceNow / SAM / escalation (only outside `-WhatIf`); forces all Microsoft mail through triage. |
| `scripts/Get-EnterpriseAppInventory.ps1` | Inventory + auto risk-tier + orphaned-app + critical-permission scan (read-only). |
| `scripts/New-HelpDeskPAG.ps1` | Stands up the role-assignable PAG with Helpdesk Administrator, Authentication Administrator and a custom app-assignment role; PIM-eligible technicians. |
| `scripts/Add-AppAccessGroup.ps1` | A2 Application Access: assign a group to an app role (naming check, nested-group guard, existing-assignment check). The manual path for the group→app-role binding. |
| `scripts/Repair-ImmutableId.ps1` | **Identity Engineering only.** Prepares a cloud-only account for hard match; refuses synced users and privileged targets. |
| `scripts/Export-AccessCertification.ps1` | Per-app access roster for owner certification. |
| `tests/HelpDeskEntra.Tests.ps1` | Pester 5 tests for the routing matrix and the triage `-WhatIf` gate. No tenant needed. |
| `*.ps1.txt`, `lib/*.psm1.txt` | Plain-text copy beside every script and the module, for mail systems that block `.ps1` attachments. Rename to drop `.txt` before use. |

The four `documents/*.docx` are also browsable on the site:
<https://whalermike.github.io/uiao/customer-documents/operational-guides/helpdesk-entra-operations/>

## Quick start

```powershell
Install-Module Microsoft.Graph -Scope CurrentUser
# preview everything first — all state-changing scripts honor -WhatIf
.\scripts\Get-EnterpriseAppInventory.ps1
.\scripts\Invoke-RequestTriage.ps1 -MailboxUpn 'helpdesk@agency.gov' -WhatIf
```

Read **`documents/Helpdesk-Flow.docx`** first for the recommendation and the
ServiceNow mechanisms; `implementation-path.md` for the authority matrix and the
kit layers. Search the scripts for `# CONFIGURE:` for the values you must supply
(tenant id, shared mailbox, ServiceNow + SAM endpoints/auth).

> Reference implementation for review/adaptation — correct against current
> Microsoft Graph PowerShell and ServiceNow's documented capabilities, not
> validated against a live tenant. Dry-run with `-WhatIf` before removing guards.
> The Entra ID Spoke requires ServiceNow Integration Hub; without it, every
> "Spoke" execution becomes a manual Help Desk task and the flow shape is unchanged.
