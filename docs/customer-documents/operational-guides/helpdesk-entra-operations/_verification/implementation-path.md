# Verification — Hybrid AD → Entra ID Help Desk / Cloud Services Implementation Path

Claim-by-claim pass over `kit/implementation-path.md` (kit v1.6, plain Markdown shipped in the zip), October 27, 2026. The routing table and the Layer 2/3 role corrections had already been checked against Microsoft and ServiceNow sources in the sibling kit documents (`help-desk-administrative-responsibilities.qmd`, `helpdesk-flow.qmd`) and in Modernization Workbook Book 15 chapters 03 and 04 and Book 04 chapters 05, 06 and 09; those rows are recorded as verified with those sources and their access dates. Remaining claims were checked today on Microsoft Learn through the Learn MCP fetch and search tools (Graph permissions reference, grant an appRoleAssignment to a group, manage groups, assign roles with administrative unit scope, PIM role settings, grant tenant-wide admin consent, first-party app tenant IDs) and on the ServiceNow Zurich Microsoft Entra ID spoke page. Three corrections came from coordinator findings in sibling verifications (rows 6, 19, 23) and were re-checked against the cited pages. Kit script and module behavior was read from `scripts/` but not changed. No personal data sent anywhere. Authority levels, approvers, tiers and cadences are program design; a one-line design-guidance blockquote was added near the top.

## Claims log

| # | Claim (short) | Where | Verdict | Source |
|---|---|---|---|---|
| 1 | Operating model: Cloud Services is higher-level review; approval sits with manager/owner | §0 | restated-as-design | — |
| 2 | Approval is not identity verification; phishing-resistant sign-in or re-proofing, never email/caller ID/knowledge questions; notify out of band | §0 | restated-as-design (ladder verified in the Administrative Responsibilities Guide: NIST SP 800-63B-4 §4.2, CISA AA23-320A) | help-desk-administrative-responsibilities.qmd (Oct 21, 2026) |
| 3 | Supervisor gate replaced by requester's manager for licenses/OneDrive | §0 | restated-as-design | — |
| 4 | A0–A3 / OOS authority levels and triage rule | §1 | restated-as-design | — |
| 5 | Password reset, cloud-only: spoke Reset Password; Password / Helpdesk Administrator | §1 table | verified | ServiceNow Zurich Entra ID spoke (Password Management actions, Oct 27, 2026); Learn delegate-by-task (Oct 21, 2026) |
| 6 | Sign-in / audit-log retrieval via Spoke (Audit logs) | §1 table | corrected: split into sign-in log lookup (Spoke, Look up Sign Ins Stream) and directory audit-log lookup (Manual); both Reports Reader | ServiceNow Zurich Entra ID spoke, Audit Logs category (Oct 27, 2026); delegate-by-task |
| 7 | Password reset, synced user: manual, Entra admin center with writeback, not M365 admin center | §1 table | verified | helpdesk-flow.qmd footnote (concept-sspr-writeback; password-writeback-microsoft-365-admin-center, Oct 21, 2026) |
| 8 | MFA / method reset manual — spoke has no method-reset action; Authentication Administrator | §1 table | verified | ServiceNow spoke (only Reset Password; User Authentication = Revoke User SignIn Sessions), Oct 27, 2026; privileged-roles-permissions (Oct 21, 2026) |
| 9 | TAP manual; Authentication Administrator for members | §1 table; Layer 2 | verified | howto-authentication-temporary-access-pass (Oct 21, 2026) |
| 10 | License, user, group management via spoke; License / User / Groups Administrator | §1 table | verified | ServiceNow spoke categories (Oct 27, 2026); delegate-by-task |
| 11 | OneDrive created on first browse; pre-provisioning by SharePoint Administrator | §1 table | verified | pre-provision-accounts (admin guide footnote, Oct 21, 2026) |
| 12 | Group→app-role binding manual until a pilot proves Create Application Assignment | §1 table | verified (spoke lists Create Application Assignment) / design for the pilot gate | ServiceNow spoke, Application Management (Oct 27, 2026) |
| 13 | Device enable/disable/delete OOS — spoke has none | §1 table | verified (Device Management actions are group add/remove/lookups only) | ServiceNow spoke (Oct 27, 2026) |
| 14 | Admin Consent: IGO only, Help Desk triage + escalate | §1 table; §3 | restated-as-design | — |
| 15 | ImmutableID repair is Identity Engineering, usually in AD (`mS-DS-ConsistencyGuid`) | §1 table; Layer 3 | verified | how-to-connect-install-existing-tenant (Oct 27, 2026; admin guide footnote) |
| 16 | Microsoft mail force-classified A3; sender doesn't prove genuineness; proof in audit log | §1 hard rule | restated-as-design (classifier rule confirmed in `Invoke-RequestTriage.ps1`) | — |
| 17 | PIM sends from `MSSecurity-noreply@`; access reviews and ID Protection from `azure-noreply@` | §1 hard rule | verified | pim-email-notifications; ops-guide-ops Notifications (admin guide footnotes, Oct 21, 2026) |
| 18 | First-party apps excluded from both Microsoft owner tenants | Layer 1 | verified (`f8cdef31-…` Microsoft Services; `72f988bf-…` Microsoft tenant) | verify-first-party-apps-sign-in (Oct 27, 2026) |
| 19 | Critical permissions include `Mail.ReadWrite.All` | Layer 1 | corrected: `Mail.ReadWrite` (no `.All` form exists) | Graph permissions reference (Oct 27, 2026) |
| 20 | Owners on the service principal and, for home-tenant apps, the application object | Layer 1 | verified | app-objects-and-service-principals; overview-assign-app-owners (workbook b04 ch05, Oct 20, 2026; owners page Oct 27, 2026) |
| 21 | Orphaned → Tier 1; critical permissions → Tier 1; externally published by hand | Layer 1 | restated-as-design | — |
| 22 | No single built-in role covers all Help Desk work | Layer 2 | verified | permissions-reference (workbook b15 ch04 ledger row 1) |
| 23 | "MFA on activation" | Layer 2 | corrected: Conditional Access authentication context (phishing-resistant strength) on activation; PIM's MFA option doesn't set the method and may not prompt | pim-how-to-change-default-settings (Oct 27, 2026) |
| 24 | Role-assignable group "(a Privileged Access Group, now called PIM for Groups)" | Layer 2 | corrected: role-assignable group whose membership PIM for Groups manages; "privileged access groups" was the feature's name until January 2023 | concept-pim-for-groups (Oct 21, 2026) |
| 25 | Helpdesk Admin (resets, session revocation) / Password Admin narrower; Authentication Admin (methods, re-registration, TAP) | Layer 2 | verified | privileged-roles-permissions; delegate-by-task (Oct 21, 2026) |
| 26 | Custom role with only `servicePrincipals/appRoleAssignedTo/update`; each assignee needs P1 | Layer 2 | verified | custom-enterprise-apps (Oct 21, 2026) |
| 27 | Application Administrator can grant consent and create enterprise apps | Layer 2 | verified | grant-admin-consent Prerequisites (Oct 27, 2026); delegate-by-task |
| 28 | Hybrid Identity Administrator cannot write `onPremisesImmutableId` | Layer 2 | verified | Graph "Working with users" sensitive actions (admin guide footnote, Oct 21, 2026) |
| 29 | `-DirectoryScopeId` scopes "the roles" to an AU | Layer 2 | corrected: Helpdesk, Password and Authentication Administrator take AU scope; the custom app-assignment role (service-principal permission only) can't, so tenant or single-app scope | manage-roles-portal "Roles that can be assigned with administrative unit scope" (Oct 27, 2026); custom-enterprise-apps |
| 30 | Technicians PIM-eligible, nothing standing | Layer 2 | restated-as-design (eligible assignment is a PIM feature) | concept-pim-for-groups |
| 31 | Only Privileged Authentication and Global Administrators can reset role-assignable group members | Layer 2 | verified | privileged-roles-permissions (Oct 21, 2026) |
| 32 | 8-hour ceiling (within PIM's 1–24 h); ticket number not validated | Layer 2 | verified | pim-how-to-change-default-settings (Oct 27, 2026) |
| 33 | 180-day eligibility with quarterly review | Layer 2 | restated-as-design | — |
| 34 | Role-assignable groups need P1; PIM activation P2 / ID Governance | Layer 2 licensing | verified | groups-concept (Oct 21, 2026) |
| 35 | Triage reads the shared mailbox Inbox with `Mail.ReadWrite.Shared` + Full Access | Layer 3 | verified (delegated: mail "a user has permission to access, including their own and shared mail") | Graph permissions reference (Oct 27, 2026) |
| 36 | Add-AppAccessGroup scopes `Application.Read.All`, `Group.Read.All`, `AppRoleAssignment.ReadWrite.All` | Layer 3 | verified (least privileged for group appRoleAssignment: `AppRoleAssignment.ReadWrite.All` and `Group.Read.All`; `Application.Read.All` resolves the service principal) | group-post-approleassignments (Oct 27, 2026) |
| 37 | Add-AppAccessGroup refuses nested groups | Layer 3; §3 | corrected (code precision): refuses unless `-AllowNestedGroups` is passed | `scripts/Add-AppAccessGroup.ps1` |
| 38 | ImmutableID script refuses synced users, `onPremisesObjectIdentifier` set, role holders | Layer 3 | verified (matches platform blocks) | how-to-connect-install-existing-tenant (Oct 27, 2026) |
| 39 | Entra doesn't honor nested groups for app assignment; only direct members get access | §3 | verified | how-to-manage-groups "Add a group to another group"; group-post-approleassignments (Oct 27, 2026) |
| 40 | Admin Consent is tenant-wide and permanent until revoked | §3 | verified (granted for the whole organization; delegated grant expiry fields ignored) | grant-admin-consent (Oct 27, 2026); New-MgBetaOauth2PermissionGrant (workbook b04 ch05, Oct 20, 2026) |
| 41 | Hard match only when a new object arrives from AD; since July 1, 2026 blocked for `onPremisesObjectIdentifier` / privileged targets; keep blocked except planned takeover | §3 | verified | how-to-connect-install-existing-tenant (Oct 27, 2026) |
| 42 | Layer 0: AD supplied the structure implicitly (OUs, `manager`, groups); interim manager/department from current source; HR seam | Layer 0 | restated-as-design (Entra has no OU tree; administrative units are the scoping equivalent — verified in the admin guide) | administrative-units (Oct 21, 2026) |
| 43 | Spoke coverage changes between releases; validate before setting `Spoke` | §5 | restated-as-design | — |
| 44 | Not tenant-tested; `-WhatIf` on every state-changing script | §4–§5 | restated-as-design (code property, not platform) | — |

## Totals

verified 26 · corrected 6 · restated-as-design 12 · couldn't-verify 0

(Row 12 is counted as verified; row 37 is a code-precision correction counted under corrected.)

## Corrections that change meaning

- Row 6: "Sign-in / audit-log retrieval — Spoke (Audit logs)" → two rows: "Sign-in log lookup — Spoke (Look up Sign Ins Stream) — Reports Reader" and "Directory audit-log lookup — Manual — Reports Reader"; the gap list now names directory audit-log lookups. Source: ServiceNow Zurich Entra ID spoke, https://www.servicenow.com/docs/bundle/zurich-integrate-applications/page/administer/integrationhub/concept/microsoft-azure-ad-spoke.html (accessed Oct 27, 2026).
- Row 19: `Mail.ReadWrite.All` → `Mail.ReadWrite`. Source: Microsoft Graph permissions reference, https://learn.microsoft.com/graph/permissions-reference (accessed Oct 27, 2026).
- Row 23: "MFA on activation" → "Conditional Access authentication context (phishing-resistant strength) on activation". Source: Microsoft Learn, "Configure Microsoft Entra role settings in Privileged Identity Management," https://learn.microsoft.com/entra/id-governance/privileged-identity-management/pim-how-to-change-default-settings (accessed Oct 27, 2026).
- Row 29: "scopes the roles to an AU" → only the user-facing roles take AU scope; the custom app-assignment role stays tenant- or app-scoped. Source: Microsoft Learn, "Assign Microsoft Entra roles," https://learn.microsoft.com/entra/identity/role-based-access-control/manage-roles-portal (accessed Oct 27, 2026).
- Row 24: a role-assignable group is not itself "PIM for Groups"; the group's membership is managed by PIM for Groups. Source: concept-pim-for-groups (accessed Oct 21, 2026).
- Row 37 (code): nested-group refusal has an `-AllowNestedGroups` override.

## Couldn't verify

None.
