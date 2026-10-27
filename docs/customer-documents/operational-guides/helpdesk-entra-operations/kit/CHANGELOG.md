# Help Desk / Cloud Services Entra ID Operations Kit — changelog

## v1.6 — October 2026 (draft)

Brings the kit into line with Microsoft's and ServiceNow's current documentation
(checked October 2026). Every correction below has a Microsoft Learn or ServiceNow
source in the documents' footnotes.

### Routing matrix (`lib/HelpDeskEntra.psm1`, implementation path, Helpdesk-Flow)

- **MFA reset → Manual.** The Entra ID spoke has no authentication-method action;
  its user-authentication category lists only Revoke User SignIn Sessions.
- **New `TemporaryAccessPass` row** (A1, Manual, Authentication Administrator).
- **Device enable / disable / delete → out of scope (device team).** The spoke
  covers device group membership only.
- **Password reset split by sync state.** A text match routes to a conservative
  Manual row; `Resolve-RequestRoute -TargetSynced` selects cloud-only (Spoke) or
  synced (Manual — Entra admin center with password writeback, never the
  Microsoft 365 admin center, else on-prem AD).
- **Enterprise app access → Manual** for the group→app-role binding until a pilot
  proves the spoke's Create Application Assignment handles group assignments.
- **ImmutableID repair → Identity Engineering.** The Help Desk detects and
  escalates; `TeamRole = TriageEscalateOnly`, no Help Desk role.
- **New `Verification` column.** Password, MFA and Temporary Access Pass rows are
  `IdentityProof`: verify the person before acting. An A0 reset still needs it —
  "Approver: None" no longer reads as "no check".
- Least-privileged roles per row: Password Administrator (resets), License
  Administrator (licenses), Reports Reader (logs), custom app-assignment role
  (app access, certification revocation).
- License regex anchored with word boundaries (`\b[eg][35]\b`, `\bsku\b`);
  `TemporaryAccessPass` and `passkey` keywords added.

### Roles

- Help Desk PAG defaults: **Helpdesk Administrator** (resets), **Authentication
  Administrator** (methods, TAP), and a **custom role** holding only
  `microsoft.directory/servicePrincipals/appRoleAssignedTo/update`, replacing
  **Application Administrator** (which can grant consent).
- **Hybrid Identity Administrator removed**: it cannot write
  `onPremisesImmutableId`.
- `New-HelpDeskPAG.ps1`: new defaults; refuses Application, Cloud Application,
  Hybrid Identity, Global, Privileged Authentication and Privileged Role
  Administrator; `-CreateAppAssignmentRole`; `-DirectoryScopeId` for AU scope;
  idempotency check honours scope; eligibility 180 days; Tier 2 PIM guidance (8 h
  ceiling; PIM does not validate ticket numbers). `PimGroups` scope set gains
  `User.ReadBasic.All` for `Get-MgUser`.

### Documents

- Removed: "Helpdesk Administrator covers only password resets", "temporarily
  disable MFA", MSOnline / `Set-MsolUser`, "role-assignable groups need P2" (P1;
  PIM needs P2), the single-sender Microsoft notification check, and the Help Desk
  ImmutableID reset procedure.
- Added: identity-verification ladder and target check; Temporary Access Pass and
  MFA recovery procedure; "capability is not authority"; AU and restricted
  management AU limits; the July 1, 2026 hard-match protections.
- Entra log retention corrected: **7 days (Free) / 30 days (P1/P2)** for audit and
  sign-in logs, 30 days for PIM audit — not "30 free / 90 P1-P2".
- Helpdesk-Flow: transport rule uses `-RedirectMessageTo` (not `-BlindCopyTo`) in
  `Audit` mode first; Reset Password does accept an application permission
  (`User-PasswordProfile.ReadWrite.All`) — only Change Password and Revoke User
  SignIn Sessions are delegated-only; triage check order; approval due dates
  reject, never approve.
- OneDrive: path limit is 400 characters decoded (260 is Windows-side); OneDrive is
  created on first browse, pre-provisioning is a SharePoint Administrator task (not
  Global Reader in the Microsoft 365 admin center); sign-in-log reads use Reports
  Reader / Security Reader, not Application Administrator.
- Three diagrams updated to match (PAG eligible roles, ServiceNow pipeline, SAM
  pipeline).

### Scripts

- `Invoke-RequestTriage.ps1`: **ServiceNow / SAM / escalation connectors now run
  inside the `ShouldProcess` gate** — v1.5 called them before it, so `-WhatIf`
  would still have created work items once the connectors were wired. Reads the
  **Inbox** folder only (`Get-MgUserMailFolderMessage -MailFolderId Inbox`), not
  every folder. Scope **`Mail.ReadWrite.Shared`** for delegated access to a shared
  mailbox. Microsoft sender rule widened to subdomains. Report gains a
  `Verification` column.
- `Get-EnterpriseAppInventory.ps1`: `InventoryRead` no longer includes
  `AppRoleAssignment.ReadWrite.All` (read-only scopes only). Owners read from the
  **application object** as well as the service principal for tenant-registered
  apps (v1.5 marked most of them orphaned). Excludes both Microsoft owner tenants
  (`f8cdef31-…` and `72f988bf-…`). Delegated scopes now count toward the risk
  tier; the docstring no longer claims externally-published detection.
- `Add-AppAccessGroup.ps1`: scope set `AppAssignment` = `Application.Read.All`,
  `Group.Read.All`, `AppRoleAssignment.ReadWrite.All` (was `Group.ReadWrite.All` +
  `Application.ReadWrite.All`). Docstring says naming is *checked*, not enforced.
  Refuses ambiguous display names; escapes quotes in OData filters; existing
  assignment check retained.
- `Repair-ImmutableId.ps1`: **Identity Engineering only.** Refuses synced users
  (fix `mS-DS-ConsistencyGuid` in AD), users with `onPremisesObjectIdentifier` set
  (read from Graph beta), and users holding or eligible for any directory role.
  `-SourceAnchorGuid` (alias `-OnPremObjectGuid`) reflects that the anchor may be
  `mS-DS-ConsistencyGuid` or `objectGUID`.
- `Export-AccessCertification.ps1`: direct-user rows carry the resolved **UPN**
  (v1.5 put the display name in `UserUpn`); paging (`-All`) on assignments.
- All scripts load the module from `..\lib\` (kit layout) or alongside the script
  (repo layout), so they run from either.
- **New:** `tests/HelpDeskEntra.Tests.ps1` (Pester 5, 26 tests): routing rows,
  password split, regex boundaries, scope sets, and an AST check that every
  connector and mail-state call sits inside the `-WhatIf` gate.

## v1.5 — June 9, 2026

Accuracy fixes from the Entra ID Spoke action table: password reset split
cloud-only vs hybrid/federated; spoke "Not supported" entries clarified as
personal-account-only; commercial Graph endpoint noted.
