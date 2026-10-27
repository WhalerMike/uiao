# Hybrid AD → Entra ID — Help Desk / Cloud Services Implementation Path

**Audience:** Cloud Services Team, Identity Engineering, IT Leadership
**Scope:** The existing Hybrid Active Directory → Microsoft Entra ID environment
**Status:** Reference implementation for agency review and adaptation — kit v1.6
**Companion code:** `scripts/` (Microsoft Graph PowerShell) · `lib/HelpDeskEntra.psm1`

> This document turns the three governance documents into an executable path.
> It contains **no product names beyond the platforms you already run** —
> Microsoft Entra ID, ServiceNow, and SAM (your SailPoint IGA). It is written
> to be handed to the agency as-is.

> **Design guidance.** The authority levels, approval layers, ownership rules, risk tiers and review cadences here are the program's design guidance for the agency to adopt or adjust; platform behavior is footnoted to Microsoft, ServiceNow and SailPoint sources.

---

## 0. The operating model this is built to

The Cloud Services Team does not need to sit in the
approval loop for routine help desk work. So this implementation is built on
one rule:

> **The Cloud Services Team is a higher-level review if the Help Desk is unable
> to perform the task. Their role is then to ensure that, if that task is routine,
> a path is created for Help Desk service. Approval and responsibility sit with the
> requester's manager (or the relevant owner), scaled to the authority the task
> actually requires.**

Everything flows from that. Requests are never handled as ad-hoc email to the
team; they are **triaged into ServiceNow or SAM**, approved there by the right
manager/owner, and only then returned to the team as governed, executable work.

**Approval is not identity verification.** A manager can approve that an MFA
reset *should* happen; only verification proves the caller *is* the account's
owner. Every password reset (including A0 resets that need no approval), MFA
reset and Temporary Access Pass carries `Verification = IdentityProof` in the
matrix: the technician checks the target, verifies the person by a
phishing-resistant sign-in or re-proofing — never email, caller ID, a
caller-supplied callback number or knowledge questions — and notifies the user out
of band afterwards. The ladder is in the Administrative Responsibilities Guide,
"Verify the person before a credential action".

**Where this intentionally differs from the source documents:** the Help Desk
guide inserts *"Help Desk Supervisor approval"* on several routine tasks
(MFA reset, license, OneDrive provisioning). For licenses and OneDrive that gate is
**replaced** by the **requester's manager**, because a senior peer team approving
each other's routine work adds latency without adding control. MFA resets and
Temporary Access Passes keep **the Help Desk supervisor or the requester's
manager** as approver, because they hand over an account.

---

## 1. The Task Authority & Routing Matrix (the spine)

This single table decides, for any incoming request: how much authority it
needs, who approves it, which system it is triaged into, and what the team
does. It is encoded as **data** in `lib/HelpDeskEntra.psm1`
(`$RequestRoutingTable`) so the classifier and the human runbook can never
drift apart — and so the agency can extend it without code changes.
`tests/HelpDeskEntra.Tests.ps1` (Pester 5) pins the rows below.

> **Intake is ServiceNow-first.** How an email becomes a triaged ServiceNow record
> and gets routed to the right pipeline — the Exchange redirect, the Inbound Email
> Action, the reroute Business Rule, and the Entra ID Spoke execution mapping — is
> the subject of the companion **Helpdesk-Flow** document. ServiceNow is the single
> front door; this matrix is the decision logic it applies.

| Authority | Meaning | Approver (owns responsibility) | Triaged to | Team role |
|-----------|---------|--------------------------------|------------|-----------|
| **A0** | No approval — routine (verification still applies) | none | **ServiceNow** (record) | Execute |
| **A1** | Manager sign-off | **Supervisor or requester's manager** | **ServiceNow** | Execute after approval |
| **A2** | Access governance | Manager **+ Application Owner** | **SAM** → ServiceNow exec | Execute after approval |
| **A3** | High authority | **IGO / Identity Eng** | **SAM** escalate → exec | Triage and escalate; Identity Engineering executes |
| **OOS** | Out of scope | Security Admin / Identity Eng / device team | **Escalate out** | Does not execute |

### Task → authority → destination

`Execution` is the recommended default execution path, checked against what
ServiceNow's Microsoft Entra ID spoke page documents (see the crosswalk in
Helpdesk-Flow): **Spoke** = ServiceNow Flow Designer auto-executes via the Entra
ID Spoke; **Manual** = SCTASK to the Help Desk; **Escalate/OOS** = out of this
team's hands. `Role` is the least-privileged role the Help Desk activates.

| Incoming request | Authority | Approver | Verify the person | Execution | Role |
|---|---|---|---|---|---|
| Password reset — cloud-only user | A0 | none | **Yes** | Spoke (Reset Password covers users created in Entra ID only) | Password / Helpdesk Administrator |
| Password reset — synced user | A0 | none | **Yes** | Manual — Entra admin center with password writeback (not the Microsoft 365 admin center), else on-prem AD | Password / Helpdesk Administrator |
| OneDrive client-side fix (cache, sign-out/in, KFM, reinstall) | A0 | none | No | Manual (client) | — |
| UPN-change re-sign-in guidance | A0 | none | No | Manual (guidance) | — |
| Sign-in log lookup (triage) | A0 | none | No | Spoke (Look up Sign Ins Stream)[^sn-spoke-audit] | Reports Reader |
| Directory audit-log lookup (triage) | A0 | none | No | Manual — the spoke has no directory-audit action | Reports Reader |
| MFA / auth-method reset | A1 | Supervisor or requester's manager | **Yes** | **Manual** — the spoke has no method-reset action | Authentication Administrator |
| Temporary Access Pass (lost every method) | A1 | Supervisor or requester's manager | **Yes** (re-proof) | Manual | Authentication Administrator |
| License assignment / change | A1 | Requester's manager | No | Spoke (License mgmt) | License Administrator |
| User enable / update / assign manager | A1 | Requester's manager | No | Spoke (User mgmt) | User Administrator |
| OneDrive provisioning (needs license) | A1 | Requester's manager | No | Manual — created on first browse; pre-provisioning by a SharePoint Administrator | — |
| **Enterprise App group access (Application Access)** | **A2** | Manager **+ Application Owner** | No | SAM connector for membership; group→app-role binding **Manual** until a pilot proves the spoke's Create Application Assignment handles it | Custom app-assignment role |
| Access-certification revocation | A2 | SAM certification (App Owner) | No | Spoke (Group mgmt) | Custom app-assignment role |
| Group creation + owner add/remove | A2 | App Owner + Identity Eng | No | Spoke (Group mgmt) | Groups Administrator |
| User create / disable (joiner / leaver) | A2 | Manager + HR / Owner (SAM lifecycle) | No | Spoke (User mgmt) | User Administrator |
| Device enable / disable / delete | **OOS** | Device team | No | Device team — the spoke has no device enable/disable/delete | — |
| **Admin Consent request** | **A3** | **IGO only** (App Owner sponsors) | No | Escalate-only | **Triage + escalate ONLY** |
| ImmutableID repair | A3 | Identity Eng Lead **+ IGO** | No | **Identity Engineering**, usually in AD (`mS-DS-ConsistencyGuid`) | Help Desk: detect + escalate only |
| Conditional Access change | OOS | Security Admin + IGO | No | Manual (Security) | — |
| Directory-role assignment | OOS | Identity Eng + IGO | No | Manual (Identity Eng) | — |
| Service Principal / App Registration | OOS | App Owner + Identity Eng | No | Manual (Identity Eng) | — |
| Organization (tenant) info | OOS/ref | Identity Eng | No | Manual (Identity Eng) | — |

**The triage rule, in one line:**
`A0/A1 → ServiceNow · A2/A3 → SAM (→ ServiceNow exec) · OOS → escalate out`.
**Execution rule:** prefer the **Entra ID Spoke** auto-action **where the spoke
documents one**; fall to a **Manual** SCTASK (Help Desk first; Cloud Services only
when the Help Desk can't) for the gaps — MFA resets and Temporary Access Passes,
synced-user password resets, directory audit-log lookups, OneDrive, Conditional Access, and the group→app-role
binding. ImmutableID repair is not a Help Desk gap: it is Identity Engineering's.

**Password resets and sync state.** Email triage can't see whether the target is
cloud-only or synced, so a password-reset match routes to a conservative **Manual**
row. Once the target's `onPremisesSyncEnabled` is known, call
`Resolve-RequestRoute -Text ... -TargetSynced $false` (Spoke) or `$true` (Manual).

**The target check.** Email triage also can't see whether the target holds a
directory role (active or eligible), is a member or owner of a role-assignable
group, or sits in a restricted management AU. The executor checks before any
credential action; any hit escalates to Identity Engineering or a Tier 0 holder.

### Hard rule: Microsoft notification mail is never direct

Any message from **`@microsoft.com`** or a subdomain is force-classified as **A3,
triage-and-escalate only**. It is never actioned from the email and never allowed
to fall through to a lower-authority rule. The sender check routes; it does not
prove a message genuine — Microsoft uses several senders (`MSSecurity-noreply@`
for PIM, `azure-noreply@` for access reviews, ID Protection and more), and
look-alikes exist. The proof is the matching event in the Entra audit log. Admin
Consent is approved by the IGO alone; the team's role is to verify in the audit log
and escalate.

---

## 2. Implementation layers

### Layer 0 — Ownership & structure foundation *(the part AD used to provide)*

Every approval path above routes through a **manager** or an **owner**. That
mapping — *which user belongs to which department, and who owns which
application* — is exactly what Active Directory used to supply implicitly (OUs,
the `manager` attribute, group structure). As AD is retired, that topology has
to be sourced explicitly.

- **Today (interim):** derive the manager/department mapping from the current
  internal source — the `manager` and `department` attributes as they flow into
  Entra from the existing directory. SAM holds the authoritative owner ↔
  application mapping.
- **Future:** the same structure is fed from the authoritative HR system. The
  implementation treats the source as a **swappable seam** — the governance and
  execution layers above do not change when the source changes.

Keep this layer's name neutral (e.g. *"Access Authority Map"*). It is the
foundation the matrix sits on.

### Layer 1 — Inventory, ownership & risk *(prerequisite to everything)*

Run **`scripts/Get-EnterpriseAppInventory.ps1`**. It enumerates every
Enterprise Application (excluding Microsoft first-party apps from both Microsoft
owner tenants unless `-IncludeMicrosoftFirstParty`)[^ms-first-party] and produces, per app: owner
status, the application permissions and delegated scopes it holds, and an
**auto-assigned risk tier**:

- **Orphaned apps (no owner) → auto-Tier 1.** Owners are read from the service
  principal *and*, for apps registered in this tenant, from the application object
  (App registrations), where they are usually recorded. An app with no accountable
  owner has no one to route its approvals through — fix these first.
- **Apps holding critical permissions** (application permissions or delegated
  scopes such as `Mail.ReadWrite`, `Mail.Send`,[^ms-graph-perms]
  `RoleManagement.ReadWrite.Directory`, …) **→ Tier 1.**
- **Externally published apps** are not detected by the script; raise them to
  Tier 1 by hand from the Application Registry.

Output: `app-inventory.csv`. This is the catalog SAM and the matrix operate on.
The script is read-only and connects with read scopes only.

### Layer 2 — Help Desk capability (the PAG)

Run **`scripts/New-HelpDeskPAG.ps1`**. Entra ID has **no single built-in role**
that covers all Help Desk identity work, so capability is delivered through a
**role-assignable group** whose membership is managed just-in-time by **PIM for
Groups** (until January 2023 Microsoft called that feature "privileged access
groups", hence "PAG"):[^ms-pim-groups]

- Roles are assigned to the **group**, never to individuals. The defaults are the
  least-privileged roles for each task: **Helpdesk Administrator** (password
  resets, session revocation — or the narrower Password Administrator),
  **Authentication Administrator** (methods, MFA re-registration, Temporary Access
  Pass for members), and a **custom enterprise-app assignment role** holding only
  `microsoft.directory/servicePrincipals/appRoleAssignedTo/update`
  (`-CreateAppAssignmentRole` creates it; each assignee needs Entra ID P1).
- **Application Administrator** (can grant consent, create enterprise apps) and
  **Hybrid Identity Administrator** (cannot write `onPremisesImmutableId`) are not
  Help Desk roles. The script refuses them.
- `-DirectoryScopeId '/administrativeUnits/<id>'` scopes the Helpdesk, Password
  and Authentication Administrator roles to an AU. The custom app-assignment role
  holds only a service-principal permission, so it can't take AU scope; assign it
  at tenant scope or to a single application.[^ms-au-scope] For one role per
  group and scope, run the script once per group.
- The technicians are **PIM-eligible members** — they hold nothing standing; they
  activate just-in-time. Membership also protects them: only Privileged
  Authentication and Global Administrators can reset a role-assignable group's
  members.
- Activation policy (apply + verify in portal; Tier 2 values): **8-hour** ceiling,
  **Conditional Access authentication context (phishing-resistant strength) on
  activation**,[^ms-pim-settings] **justification and ticket number required** (PIM does
  not validate the number — correlate activations to tickets in the SIEM),
  **180-day** eligibility with quarterly review.

> Licensing: role-assignable groups require Entra ID **P1**; PIM activation
> requires **P2 / Entra ID Governance**.[^ms-rag]

### Layer 3 — Operations (the runbook, with code)

| Task | Script | Notes |
|---|---|---|
| Triage intake → route | `Invoke-RequestTriage.ps1` | Reads the shared mailbox's **Inbox** only (`Mail.ReadWrite.Shared` + Full Access); applies §1 matrix; opens ServiceNow/SAM items **only inside the `-WhatIf` gate** |
| Application Access (A2) | `Add-AppAccessGroup.ps1` | Requires `-ApprovalRef`; **checks** (does not enforce) naming; **refuses nested groups** (override: `-AllowNestedGroups`); skips an existing assignment; scopes `Application.Read.All`, `Group.Read.All`, `AppRoleAssignment.ReadWrite.All` |
| ImmutableID preparation (A3) | `Repair-ImmutableId.ps1` | **Identity Engineering only**, for cloud-only accounts being taken over; **refuses synced users** (fix `mS-DS-ConsistencyGuid` in AD), users with `onPremisesObjectIdentifier` set, and role holders (blocked since July 1, 2026); dual-approval params; `-WhatIf` aware |
| Quarterly certification | `Export-AccessCertification.ps1` | Per-app roster for owner certify/revoke; direct-user rows carry the resolved UPN |

---

## 3. Platform realities the code enforces

1. **Entra does not honor nested groups for Enterprise App assignment.** A
   group assigned to an app grants access only to its **direct** user
   members.[^ms-nested]
   `Add-AppAccessGroup.ps1` detects nested groups and refuses to proceed unless `-AllowNestedGroups` is passed; the
   certification export lists direct members only.
2. **Admin Consent is tenant-wide and permanent until revoked.**[^ms-consent] It is never a
   Cloud Services Team action — triage, verify in the audit log, escalate to the
   App Owner → IGO. The triage classifier hard-codes this.
3. **Hard match happens only when a new object arrives from AD,** and since July 1,
   2026 Entra ID blocks hard matches to accounts with `onPremisesObjectIdentifier`
   set or with privileged roles. Keep hard matching blocked except during a
   planned takeover. `Repair-ImmutableId.ps1` refuses the cases the platform
   would block.[^ms-hardmatch]

---

## 4. Run order

```powershell
# One-time prerequisites
Install-Module Microsoft.Graph -Scope CurrentUser

# 0. Optional: run the kit's tests (no tenant needed)
Invoke-Pester .\tests

# 1. Inventory + risk + orphans (read-only)
.\scripts\Get-EnterpriseAppInventory.ps1 -OutputPath .\app-inventory.csv

# 2. Assign owners to orphaned/critical apps in Entra + SAM (Layer 1 close-out)
#    (owner assignment is a governance decision — do it from the inventory)

# 3. Stand up the Help Desk PAG (preview first)
.\scripts\New-HelpDeskPAG.ps1 -TechnicianUpns 'a@agency.gov','b@agency.gov','c@agency.gov' -CreateAppAssignmentRole -WhatIf

# 4. Turn on triage (preview first — shows routing decisions, creates nothing)
.\scripts\Invoke-RequestTriage.ps1 -MailboxUpn 'helpdesk@agency.gov' -WhatIf

# 5. Day-to-day operations
.\scripts\Add-AppAccessGroup.ps1 -AppDisplayName 'Payroll' -GroupName 'APP-PAYROLL-USERS-T1' -ApprovalRef 'RITM0045821' -WhatIf
.\scripts\Export-AccessCertification.ps1
```

Every state-changing script supports **`-WhatIf`**. Run it first.

---

## 5. What you must configure / what's deliberately left open

- **`# CONFIGURE:`** markers in the code: tenant id, the Help Desk shared
  mailbox, and the **ServiceNow** and **SAM** connector endpoints + auth. The
  connectors are scaffolded with the canonical REST shapes but are intentionally
  not wired to live systems.
- **The matrix is a starting point.** When the agency returns more accurate
  approval paths — or you discover task types not listed here — edit
  `$RequestRoutingTable` in `lib/HelpDeskEntra.psm1`. Add a row (keyword
  `Match`, `Authority`, `Destination`, `Approver`, `Verification`); nothing else
  changes. Re-run the tests.
- **Spoke coverage changes between releases.** Validate the crosswalk against the
  installed Microsoft Entra ID spoke before turning any row to `Spoke`.
- **Not tenant-tested.** This is a correct-by-construction reference against
  current Microsoft Graph PowerShell, not a package validated against your live
  tenant. Treat first runs as `-WhatIf` dry runs and confirm behavior before
  removing the guard.

---

## 6. Source-document cross-reference

| This guide | Source |
|---|---|
| §1 matrix, triage | Help Desk Guide §2, §5–§7; Governance Structure Brief §4 routing |
| Identity verification | Help Desk Guide, "Verify the person before a credential action" |
| Layer 1 risk tiers | Enterprise App Governance (Doc 3) §4, §8.3 |
| Layer 2 PAG / PIM | Help Desk Guide §3–§4 |
| Layer 3 App Access | Help Desk Guide §8; nested groups §7.4 |
| ImmutableID | Help Desk Guide, "Hybrid identity operations" |
| Certification | Doc 3 §10.3; Governance Structure Brief §6.3 / §8.4 |

[^sn-spoke-audit]: ServiceNow, *Microsoft Entra ID spoke* (Zurich), Integration Hub: the Audit Logs category lists one action, "Look up Sign Ins Stream", and no directory-audit action, <https://www.servicenow.com/docs/bundle/zurich-integrate-applications/page/administer/integrationhub/concept/microsoft-azure-ad-spoke.html> (accessed Oct 27, 2026).
[^ms-graph-perms]: Microsoft Learn, "Microsoft Graph permissions reference": the mail application permission is `Mail.ReadWrite` ("Read and write mail in all mailboxes"); there is no `Mail.ReadWrite.All`, <https://learn.microsoft.com/graph/permissions-reference> (accessed Oct 27, 2026).
[^ms-first-party]: Microsoft Learn, "Verify first-party Microsoft applications in sign-in reports": Microsoft Services tenant `f8cdef31-a31e-4b4a-93e4-5f571e91255a` and Microsoft tenant `72f988bf-86f1-41af-91ab-2d7cd011db47`, <https://learn.microsoft.com/troubleshoot/entra/entra-id/governance/verify-first-party-apps-sign-in> (accessed Oct 27, 2026).
[^ms-pim-groups]: Microsoft Learn, "Privileged Identity Management (PIM) for Groups," <https://learn.microsoft.com/entra/id-governance/privileged-identity-management/concept-pim-for-groups> (accessed Oct 21, 2026).
[^ms-au-scope]: Microsoft Learn, "Assign Microsoft Entra roles," section "Roles that can be assigned with administrative unit scope": a custom role can take AU scope only if it "include[s] at least one permission relevant to users, groups, or devices," <https://learn.microsoft.com/entra/identity/role-based-access-control/manage-roles-portal> (accessed Oct 27, 2026); and "Create custom roles to manage enterprise apps in Microsoft Entra ID" (tenant or single-app scope), <https://learn.microsoft.com/entra/identity/role-based-access-control/custom-enterprise-apps> (accessed Oct 21, 2026).
[^ms-pim-settings]: Microsoft Learn, "Configure Microsoft Entra role settings in Privileged Identity Management," sections "On activation, require multifactor authentication" (users might not be prompted if they already authenticated with strong credentials) and "On activation, require Microsoft Entra Conditional Access authentication context" (used with Authentication Strengths to require a specific method); the ticket field is information-only, <https://learn.microsoft.com/entra/id-governance/privileged-identity-management/pim-how-to-change-default-settings> (accessed Oct 27, 2026).
[^ms-rag]: Microsoft Learn, "Use Microsoft Entra groups to manage role assignments," <https://learn.microsoft.com/entra/identity/role-based-access-control/groups-concept> (accessed Oct 21, 2026).
[^ms-nested]: Microsoft Learn, "Manage Microsoft Entra groups and group membership," section "Add a group to another group" ("Nested groups don't gain access to shared resources and applications that are assigned to the parent group"), <https://learn.microsoft.com/entra/fundamentals/how-to-manage-groups>; and "Grant an appRoleAssignment to a group" ("All direct members of the group will be considered assigned"), <https://learn.microsoft.com/graph/api/group-post-approleassignments> (both accessed Oct 27, 2026).
[^ms-consent]: Microsoft Learn, "Grant tenant-wide admin consent to an application" (consent is granted "on behalf of the whole organization"), <https://learn.microsoft.com/entra/identity/enterprise-apps/grant-admin-consent> (accessed Oct 27, 2026); and "New-MgBetaOauth2PermissionGrant," parameter notes for `ExpiryTime` and `StartTime` (currently ignored), <https://learn.microsoft.com/powershell/module/microsoft.graph.beta.identity.signins/new-mgbetaoauth2permissiongrant?view=graph-powershell-beta> (accessed Oct 20, 2026).
[^ms-hardmatch]: Microsoft Learn, "Configure Microsoft Entra Connect for an existing tenant," sections "Hard match vs soft match," "Block hard match in Microsoft Entra ID" and "Hard match security protections," <https://learn.microsoft.com/entra/identity/hybrid/connect/how-to-connect-install-existing-tenant> (accessed Oct 27, 2026).
