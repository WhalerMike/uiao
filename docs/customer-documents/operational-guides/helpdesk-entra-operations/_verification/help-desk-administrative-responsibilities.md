# Verification — Help Desk Administrative Responsibilities Guide

Claim-by-claim pass over `help-desk-administrative-responsibilities.qmd` (kit v1.6), October 27, 2026. Every checkable platform claim was checked: role capabilities and target lists, license requirements, role-assignable group rules, administrative units, PIM settings and activation, Temporary Access Pass and MFA method behavior, audit and sign-in log paths, activity names and retention, admin consent roles, enterprise application assignment, Entra Connect sync, hard match and Connect Health, OneDrive and SharePoint client and admin facts, Azure Monitor alerting, the ServiceNow Microsoft Entra ID spoke, Microsoft notification senders, and the CISA and NIST citations. Primary sources opened today: Microsoft Learn through the Learn MCP search and fetch tools (privileged roles and permissions, built-in roles, groups-concept and groups-create-eligible, admin-units-members-dynamic, administrative-units, PIM role settings for roles and for groups, groups-activate-roles, PIM email notifications, grant-admin-consent, admin consent workflow, assign-user-or-group-access-portal, howto-access-activity-logs, reference-audit-activities, reference-reports-data-retention, concept-sign-in-log-activity-details, Connect Health operations, whatis-azure-ad-connect, redirect-known-folders, use-group-policy, block-file-types, manage-site-collection-storage-limits, cant-sync-after-migration, howto-troubleshoot-upn-changes, Azure Monitor ITSM secure webhook); the ServiceNow Microsoft Entra ID spoke page (Zurich) through WebFetch. Claims the Federal Modernization Workbook already verified (Book 15 Ch03, Ch04, Appendix A and their ledgers; accessed Oct 21–22, 2026) are recorded with that access date. Program policy — SLAs, approval chains, the authority boundary, escalation triggers, review cadences, PIM setting values and naming — is recorded restated-as-design; a "Design guidance" callout was added after the series notice, and "(design guidance)" markers were added to the authority boundary, PIM settings, escalation matrix and SLA lead-ins. SailPoint/SAM statements describe the agency's configuration of its IGA platform, not SailPoint product behavior, and are treated as design. No personal data was sent anywhere.

## Claims log

| # | Claim (short) | Where | Verdict | Source |
|---|---|---|---|---|
| 1 | No single Entra role covers all help desk work; Helpdesk/Password Admin reset passwords and invalidate refresh tokens; Authentication Admin manages methods, re-registration, TAP | Purpose | verified | `ms-privileged`, `ms-by-task` (Oct 21); permissions-reference (Oct 27) |
| 2 | Enterprise app assignment needs a narrow custom role, not Application Administrator | Purpose | verified | `ms-custom-apps` (Oct 21) |
| 3 | Most help desk roles act only on non-admins; none can reset a member/owner of a role-assignable group | Purpose; PAG | verified | privileged-roles-permissions "Who can reset passwords" (Oct 27) |
| 4 | Authority boundary table (authorized / not authorized) | Authority boundaries | restated-as-design | — |
| 5 | Synced-user reset in Entra admin center with writeback, not Microsoft 365 admin center | Authority boundaries | verified | Workbook App A `aA-writeback`, SSPR writeback concept (Oct 22) |
| 6 | Cloud-only resets through the Entra ID spoke (Reset Password resets Entra-created users only) | Authority boundaries | verified | ServiceNow Entra ID spoke (Zurich), Oct 27 |
| 7 | Auth Admin can delete/disable/enable users and change UPN for users in scope; User Admin can delete users, create guests | Capability callout | verified | `ms-privileged`, `ms-by-task` (Oct 21) |
| 8 | SIEM flags directory changes with no matching ticket | Capability callout | restated-as-design | — |
| 9 | Scattered Spider posed as employees to get help desk resets and MFA moves | Verify the person | verified | `cisa-spider` AA23-320A (Oct 21) |
| 10 | Verification ladder; notify by another channel; record rung not evidence | Verify the person | restated-as-design (measured against SP 800-63B-4 sec 4.2, verified `nist-63b`) | pages.nist.gov 800-63B-4 (Oct 21) |
| 11 | Entra account recovery exists for users who lost every method | Ladder | verified | Workbook Ch03 ledger #47–48 (Learn "Account recovery overview," Oct 21) |
| 12 | Target check: role (active/eligible), role-assignable group, RMAU stops the help desk | Step 1 | verified | privileged-roles-permissions (Oct 27); `ms-rmau` |
| 13 | AD OU delegation → AU + scoped role mapping table | PAG — OU replacement | restated-as-design (roles are AU-assignable: verified `ms-au-roles`) | admin-units-assign-roles (Oct 21) |
| 14 | Dynamic AU rule example `extensionAttribute2 -eq "IT"` | PAG — OU replacement | corrected: rule syntax needs the `user.` prefix; dynamic AU members need P1 each; not available in Azure Government clouds | admin-units-members-dynamic, groups-dynamic-membership (Oct 27) |
| 15 | AU-scoped roles act only on non-admin members; AUs limit changes, not visibility | PAG — AU limits | verified | `ms-au-roles` (Oct 21) |
| 16 | RMAU members administered only by roles at that unit's scope | PAG — AU limits | verified | `ms-rmau` (Oct 21) |
| 17 | Direct individual assignments can't be time-bound / approval-gated (governance rationale) | Why group-based | restated-as-design | — |
| 18 | Only PAA and GA can reset members/owners of role-assignable groups | PAG | verified | groups-concept "How are role-assignable groups protected?" (Oct 27) |
| 19 | "Privileged Access Group" was the name of PIM for Groups until January 2023 | PAG | verified | concept-pim-for-groups (Oct 27) |
| 20 | One role-assignable group per role and scope; `PRV-T2-…` naming | PAG | restated-as-design | — |
| 21 | Naming options A/B | Naming | restated-as-design | — |
| 22 | "Standard security groups and Microsoft 365 Groups cannot be used for PIM-governed role assignment" | Naming | corrected: role-assignable may be a security or Microsoft 365 group; what matters is the setting chosen at creation; creation needs Privileged Role Administrator | groups-concept; groups-create-eligible (Oct 27) |
| 23 | Role-assignable groups need P1; PIM activation P2 or ID Governance | Note | verified | `ms-rag` groups-concept (Oct 27) |
| 24 | isAssignableToRole set only at creation; no dynamic membership; no nesting; max 500 | Note | verified | groups-concept (Oct 27) |
| 25 | PIM settings are per role and shared by every holder | PIM | verified | `ms-pim-settings` (Oct 21) |
| 26 | Eligible, not active; 8-hour ceiling; 180-day eligibility; quarterly review; approval optional for Tier 2 | PIM table | restated-as-design (values); verified (1–24 h activation range) | pim-how-to-change-default-settings (Oct 27) |
| 27 | Justification and ticket fields can be required | PIM table | verified | pim-how-to-change-default-settings (Oct 27) |
| 28 | Phishing-resistant MFA required on activation | PIM table | corrected: phishing-resistance is enforced through a CA authentication context with an authentication strength; PIM's own MFA option doesn't fix the method and may not prompt again in a session | pim-how-to-change-default-settings; groups-role-settings (Oct 27) |
| 29 | Activation notifications to supervisor and Identity Engineering inbox | PIM table | verified (Notifications tab supports added recipients) | pim-how-to-change-default-settings (Oct 27) |
| 30 | Activation logged in Entra audit logs (activator, role, justification, times, approver) | Audit trail | verified | Workbook Ch04 ledger #69 (reference-audit-activities, Oct 21) |
| 31 | PIM ticket field is information-only; no correlation with ticketing | Audit trail; PIM logging | verified | pim-how-to-change-default-settings / groups-role-settings (Oct 27) |
| 32 | SIEM join of ticket numbers; flag within 24 hours | Audit trail; PIM logging | restated-as-design | — |
| 33 | Onboarding/offboarding steps; IGO approval; removal on SAM approval | Onboarding/offboarding | restated-as-design | — |
| 34 | Identity Engineering adds technician as an eligible PAG member via PIM | Onboarding | verified | concept-pim-for-groups (Oct 27) |
| 35 | Each role is the least-privileged Microsoft documents for its task | Roles table | verified | `ms-by-task` (Oct 21) |
| 36 | Helpdesk Admin target list "(other Helpdesk Admins, Message Center Reader, Reports Reader)" | Roles table | corrected: also Directory Readers, Guest Inviters, Password Admins, Usage Summary Reports Readers, User Experience Success Managers | privileged-roles-permissions "Who can reset passwords" (Oct 27) |
| 37 | Password Admin acts only on non-admins, Directory Readers, Guest Inviters, Password Admins | Roles table | verified | privileged-roles-permissions (Oct 27) |
| 38 | Auth Admin: delete/reset methods, require re-registration, TAP to members not admins or self; can't manage MFA settings or methods policy | Roles table | verified | privileged-roles-permissions "Compare authentication roles" (Oct 27); `ms-tap` |
| 39 | Custom role `servicePrincipals/appRoleAssignedTo/update`, one app or tenant, P1 per assignee | Roles table | verified | `ms-custom-apps` (Oct 21) |
| 40 | `New-HelpDeskPAG.ps1 -CreateAppAssignmentRole` creates it | Roles table | verified (kit source) | `scripts/New-HelpDeskPAG.ps1` in this repo |
| 41 | User Admin broadest optional role (delete users, guests, licenses, reset limited admins) | Roles table | verified | `ms-by-task`, `ms-privileged` |
| 42 | License Administrator least privileged for license assignment | Roles table | verified | `ms-by-task` |
| 43 | Reports Reader reads logs; Security Reader sees applied CA policies | Roles table; OneDrive | verified | howto-access-activity-logs (Oct 27); Workbook App A `aA-ca-logs` (Oct 21) |
| 44 | Application Administrator can consent to delegated and non-Graph application permissions, create enterprise apps | Roles callout | verified | grant-admin-consent (Oct 27) |
| 45 | Hybrid Identity Admin scope; not among roles that can update onPremisesImmutableId | Roles callout; Hybrid | verified | `ms-graph-users` (Oct 21) |
| 46 | PAA is the only one of these roles that can reset a privileged admin | Roles callout | verified | privileged-roles-permissions (Oct 27) |
| 47 | Three-platform model; SAM actors; three preconditions; RITM metadata | SAM integration | restated-as-design | — |
| 48 | Admin consent needs "Global Admin or Privileged Role Administrator rights" | SAM automation table | corrected: PRA for any permission; Cloud Application / Application Administrator for anything except Graph application permissions | grant-admin-consent "Prerequisites" (Oct 27) |
| 49 | Neither SAM nor the Entra ID spoke manages authentication methods | SAM automation table | verified | ServiceNow Entra ID spoke (Oct 27) |
| 50 | OneDrive created on first browse; pre-provisioning `Request-SPOPersonalSite` needs SharePoint Admin; Global Reader read-only | SAM table; OneDrive | verified | `ms-od-provision` (Oct 21); M365 admin roles (Oct 27) |
| 51 | Group creation restricted by policy; Groups Administrator | SAM table | verified (role) / design (policy) | `ms-by-task` |
| 52 | PIM sender MSSecurity-noreply@microsoft.com; azure-noreply for access reviews, Connect Health, ID Protection, app notices; SSPR other addresses | Notifications | verified | pim-email-notifications (Oct 27); `ms-ops-notify` (Oct 21) |
| 53 | Sender check is not proof; check the audit log | Notifications | restated-as-design | — |
| 54 | Admin consent emails carry "Review permissions" / "Approve" links | Admin consent callout | couldn't-verify | Learn documents reviewer emails and their timing, not link labels |
| 55 | Audit log path "Entra Portal → Monitoring → Audit Logs" | Notification step 3; consent step 4 | corrected (minor): Entra ID → Monitoring & health → Audit logs | howto-access-activity-logs (Oct 27) |
| 56 | Audit activity "Consent to application" | Consent step 4 | verified | reference-audit-activities (Oct 27) |
| 57 | Notification-type triage table; RITM type descriptions | Incoming requests | restated-as-design | — |
| 58 | Helpdesk Admin can monitor service health | Notification table | verified | permissions-reference Helpdesk Administrator (Oct 27) |
| 59 | Require re-register MFA effects; revoke sessions invalidates refresh tokens | TAP and MFA | verified | `ms-mfa-methods` (Oct 21) |
| 60 | TAP lifetimes 10 min–30 days, one-time option, 10-minute registration window, shown once, not for guests | TAP | verified | `ms-tap` (Oct 21) |
| 61 | Six-step recovery sequence; TAP policy owned by Authentication Policy Admin | TAP | restated-as-design (policy ownership verified, privileged-roles-permissions) | — |
| 62 | Admin consent triage procedure and decision tree | Admin consent | restated-as-design | — |
| 63 | Enterprise app UI steps (Users and groups, Add user/group, None Selected, Select a role, Assign, Remove) | Enterprise app | verified | assign-user-or-group-access-portal (Oct 27) |
| 64 | "If only one role exists, it will be pre-selected" | Enterprise app step 6 | corrected: if the app defines no roles, assignment uses Default Access | assign-user-or-group-access-portal (Oct 27) |
| 65 | Group-based assignment needs P1 | Enterprise app | verified | assign-user-or-group-access-portal (Oct 27) |
| 66 | PIM path "Identity Governance → PIM → My Roles → Eligible Assignments … activate the custom role" | Enterprise app step 2 | corrected: ID Governance → PIM → My roles → Groups (PAG membership) or Microsoft Entra roles → Eligible assignments | groups-activate-roles (Oct 27) |
| 67 | Authorization summary for enterprise app actions | Enterprise app | restated-as-design | — |
| 68 | Source anchor (Base64 mS-DS-ConsistencyGuid or objectGUID); matching on new objects only; fix in AD; July 1, 2026 hard-match block; block hard match by default | Hybrid | verified | `ms-hardmatch` (Oct 27) |
| 69 | `Repair-ImmutableId.ps1` refuses synced users, onPremisesObjectIdentifier set, role holders/eligibles | Hybrid | verified (kit source) | `build/helpdesk-entra-kit/.../Repair-ImmutableId.ps1` |
| 70 | `Start-ADSyncSyncCycle -PolicyType Delta` | Hybrid procedure | verified | Workbook App A `aA-scheduler` (Oct 21) |
| 71 | Sync cycle "typically 30 minutes" | Sync mismatch | verified (footnote added: 30 minutes by default) | how-to-connect-sync-feature-scheduler (Oct 21) |
| 72 | Help Desk reads Connect Health via "Entra Portal → Entra Connect → Connect Health" | Connect Health | corrected: Connect Health uses its own Azure RBAC (Reader needed; no Entra help desk role grants it); Connect Health needs P1 | how-to-connect-health-operations; whatis-azure-ad-connect (Oct 27) |
| 73 | Tier 3 escalation conditions | Hybrid escalation | restated-as-design | — |
| 74 | Expired token "most common cause" | OneDrive table | couldn't-verify | No Microsoft frequency data found |
| 75 | KFM: "disable, re-enable, or reset KFM policy in local OneDrive settings" | OneDrive table | corrected: stop/restart backup in Backup → Manage backup unless `KFMBlockOptOut` is set; policy changes are device management | redirect-known-folders; use-group-policy (Oct 27) |
| 76 | Path limit 400 characters (260 is Windows-side) | OneDrive table | verified | `ms-spo-limits` (Oct 21) |
| 77 | `onedrive.exe /reset` path | OneDrive table; step 7 | verified (footnote added) | Workbook App A `aA-od-reset` (Oct 21) |
| 78 | Site quota: "Yes — Help Desk identifies the site quota status in SharePoint Admin Center" | OneDrive table | corrected: storage limits live in the SharePoint admin center (SharePoint Administrator); help desk identifies and routes; OneDrive has a separate per-user quota | manage-site-collection-storage-limits; site-storage-quota-exceeded (Oct 27) |
| 79 | Blocked file types at "SharePoint Admin Center → Settings → Blocked file types" | OneDrive table | corrected: Settings → Sync → "Block upload of specific file types" (upload only); device policy can also exclude uploads | block-file-types (Oct 27) |
| 80 | Clear OneAuth and IdentityCache after UPN change, password change or tenant migration | Step 7(c) | verified | `ms-od-cache` cant-sync-after-migration (Oct 27) |
| 81 | CA tab: a policy showing "Failed" is the root cause | OneDrive step 3 | corrected (minor): result value is "Failure"; report-only results don't block | concept-sign-in-log-activity-details; concept-conditional-access-report-only (Oct 27) |
| 82 | Sign-in log path "Monitoring → Sign-in Logs" | OneDrive step 3; table | corrected (minor): Entra ID → Monitoring & health → Sign-in logs | howto-access-activity-logs (Oct 27) |
| 83 | Device join/compliance check in Entra Devices | OneDrive step 4 | verified (by Workbook App A diagnostics table, Oct 21) | — |
| 84 | License assignment path Users → Licenses → Assignments | OneDrive table | verified (by role, `ms-by-task`); path not separately checked | — |
| 85 | Azure Monitor alert / "Entra diagnostic rule" fires webhook that creates a ServiceNow incident | Auto-routing | corrected (minor): log search alert on Entra sign-in logs sent to Log Analytics via a diagnostic setting; action group webhook / Secure Webhook to ServiceNow | howto-integrate-activity-logs-with-azure-monitor-logs; itsm secure webhook (Oct 27) |
| 86 | Approval-by-resolution matrix; CAB for CA exceptions | OneDrive approvals | restated-as-design | — |
| 87 | UPN change "will always break" OneDrive sync | UPN callout | corrected: "might be unable to sync"; sign out, clear cached credentials, sign in | cant-sync-after-migration; howto-troubleshoot-upn-changes (Oct 27) |
| 88 | Password-reset sync errors "almost always resolve" by sign-out/in | Password callout | corrected (softened to "usually", with the documented cache-clear step) | cant-sync-after-migration (Oct 27) |
| 89 | Escalation matrix | Escalation | restated-as-design | — |
| 90 | SLA table | Audit — SLA | restated-as-design | — |
| 91 | Quarterly PAG review via SAM; auto-removal if not certified | Quarterly reviews | restated-as-design | — |
| 92 | Audit and sign-in logs 7 days Free, 30 days P1/P2; retention not retroactive; export via Azure Monitor | Retention | verified | reference-reports-data-retention (Oct 27) |
| 93 | Non-compliance reporting conditions; document control; review cycle | Compliance; control | restated-as-design | — |
| 94 | ServiceNow Entra ID spoke quoted verbatim ("provides spoke actions to automate Microsoft Entra ID tasks for …") | ServiceNow alignment | corrected: quotation no longer matches the page; replaced with paraphrase (actions to automate Entra tasks when events occur in ServiceNow; ten categories; Integration Hub subscription; Reset Password for Entra-created users only; no authentication-method reset) and the gap list gains authentication-method resets | ServiceNow Entra ID spoke (Zurich), Oct 27 |

## Totals

verified 52 · corrected 18 · restated-as-design 22 · couldn't-verify 2 (94 rows)

(Rows 10, 13, 26 and 51 mix a verified platform fact with design values; each is counted once under its leading verdict: rows 10, 13, 26 as restated-as-design, row 51 as verified.)

## Corrections that change meaning

- **Role-assignable group types (row 22).** Old: standard security groups *and Microsoft 365 groups* can't be used for PIM-governed role assignment. New: a group created without the role-assignable setting can never hold an Entra role; the setting exists for security and Microsoft 365 groups and only at creation; creation needs Privileged Role Administrator. Source: Learn "Use Microsoft Entra groups to manage role assignments"; "Create a role-assignable group."
- **Phishing-resistant MFA on activation (row 28).** Old: PIM setting requires phishing-resistant MFA. New: enforced through a Conditional Access authentication context with a phishing-resistant authentication strength; PIM's built-in MFA option doesn't fix the method and may not prompt again in a session. Source: Learn "Configure Microsoft Entra role settings in PIM"; "Configure PIM for Groups settings."
- **Helpdesk Administrator targets (row 36).** Old list of three limited roles; new full list from Microsoft's table.
- **Admin consent roles (row 48).** Old: Global Admin or Privileged Role Administrator. New: Privileged Role Administrator for any permission; Cloud Application or Application Administrator for all but Microsoft Graph application permissions. Source: Learn "Grant tenant-wide admin consent," Prerequisites.
- **PIM activation path (row 66).** Old: activate the custom role under My Roles → Eligible Assignments. New: under the PAG model the technician activates group membership (My roles → Groups), or a directly held role under Microsoft Entra roles. Source: Learn "Activate your group membership or ownership in PIM."
- **Dynamic AU rule (row 14).** Rule needs `user.` prefix; P1 per member; not available in Azure Government clouds. Source: Learn "Manage users or devices for an administrative unit with rules for dynamic membership groups."
- **Connect Health access (row 72).** Added: Azure RBAC Reader on Connect Health is required and no Entra help desk role grants it; Connect Health needs P1. Source: Learn "Microsoft Entra Connect Health operations"; "What is Microsoft Entra Connect?"
- **KFM (row 75).** Old: reset KFM policy in local settings. New: stop/restart backup in Manage backup unless `KFMBlockOptOut` blocks it; policy belongs to device management. Source: Learn "Redirect and move Windows known folders"; "Use OneDrive policies."
- **Site quota (row 78).** Old: Help Desk can resolve, checks quota in SharePoint admin center. New: Partial; SharePoint admin center needs a SharePoint Administrator; per-user OneDrive quota distinct. Source: Learn "Manage site storage limits"; "OneDrive site is read-only because storage quota was exceeded."
- **Blocked file types (row 79).** Old path "Settings → Blocked file types." New: Settings → Sync → "Block upload of specific file types" (upload only). Source: Learn "Block syncing of specific file types."
- **UPN change (row 87).** Old: "will always break" sync. New: "can"; Microsoft says OneDrive "might be unable to sync"; add the cache-clear step. Source: Learn "OneDrive for Business can't sync after tenant migration."
- **ServiceNow spoke quotation (row 94).** Old verbatim quotation not found on today's page; replaced with a sourced paraphrase, and authentication-method resets added to the residual gaps. Source: ServiceNow "Microsoft Entra ID spoke" (Zurich).

## Couldn't verify

- Row 54: the link labels ("Review permissions," "Approve") in Microsoft admin consent request emails. Learn documents who receives the emails and when, not their buttons. Text left as is; the instruction (don't act from the email) stands regardless.
- Row 74: that an expired token or signed-out client is the most common OneDrive sync cause. No Microsoft frequency data found. Text left as is.
