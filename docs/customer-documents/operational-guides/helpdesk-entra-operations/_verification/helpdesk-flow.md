# Verification — Help Desk Flow — Intake, Triage, and Routing

Claim-by-claim pass on `docs/customer-documents/operational-guides/helpdesk-entra-operations/helpdesk-flow.qmd` for kit v1.6, done October 27, 2026. ServiceNow pages (Microsoft Entra ID spoke, Microsoft Active Directory spoke, Inbound email actions, Email filters, Ask for Approval action) were opened with WebFetch. Microsoft pages were opened with the Microsoft Learn MCP tools, and each reference-list URL was checked for HTTP status and page title with curl (no identifying headers). The CISA advisory was opened with WebFetch. All sources were accessed Oct 27, 2026. The crosswalk agrees with the workbook's Oct 21, 2026 check (Book 15 Ch03, footnote c03-sn-spoke), and the ServiceNow spoke page was opened again today to confirm each row. No personal data was sent anywhere.

## Claims log

| # | Claim (short) | Where | Verdict | Source |
|---|---|---|---|---|
| 1 | Built on Email Accounts, Email Filters, Inbound Email Actions, Flow Designer, Entra ID spoke | Intro | verified | ServiceNow Email filters; Inbound email actions (Yokohama); Ask for Approval action (Yokohama); Entra ID spoke (Zurich) |
| 2 | One rule: triage in ServiceNow first, route by authority; Cloud Services is escalation review | Callout | restated-as-design | Program policy; design-guidance callout added |
| 3 | Quoted spoke sentence "provides spoke actions to automate Microsoft Entra ID tasks for …" | Integrating callout | corrected | The phrase isn't on the Zurich spoke page. Its wording is "provides actions to automate Entra tasks when events occur in ServiceNow". The quote was replaced, and the ten categories are kept as a paraphrase |
| 4 | Target architecture and diagram (front door, triage, two pipelines, spoke-or-manual) | Target architecture | restated-as-design | Program design |
| 5 | The recommendations (front door, triage by authority, automate where the spoke documents it, verify the person, Cloud Services is escalation) | Recommendations | restated-as-design | Program design. The heading says "four" but lists five; headings were left unchanged (flagged) |
| 6 | Reset Password covers users created in Entra ID only, not federated users | Crosswalk; Two limits | verified | Entra ID spoke (Zurich), Reset Password |
| 7 | Synced-user reset: Entra admin center with writeback; Microsoft 365 admin center doesn't write back | Crosswalk | verified | MS Learn SSPR writeback concept ("Supports password writeback when an admin resets them from the Microsoft Entra admin center"); M365 admin center troubleshooting article |
| 8 | Sign-in / audit-log retrieval = "Audit log actions", Spoke | Crosswalk | corrected | The Audit Logs category lists only "Look up Sign Ins Stream". The row now reads: sign-ins through the spoke; the directory audit log is manual |
| 9 | No MFA/auth-method or TAP action; user authentication lists only Revoke User SignIn Sessions | Crosswalk; Two limits | verified | Entra ID spoke, User Authentication category |
| 10 | Assign / Remove User License | Crosswalk | verified | Spoke, License Management |
| 11 | Enable / Disable / Update User | Crosswalk | verified | Spoke, User Management (the page doesn't say whether Update User sets manager) |
| 12 | Add / remove user to group; create security group; add / remove owner | Crosswalk | verified | Spoke, Group Management |
| 13 | Access-certification revocation via group membership | Crosswalk | verified | Spoke, Remove User from Group |
| 14 | Joiner/leaver user create/disable via User management | Crosswalk | verified | Spoke, Create User / Disable User |
| 15 | Device enable/disable/delete not covered; device group membership only | Crosswalk | verified | Spoke, Device Management (group and lookup actions only) |
| 16 | Create / Delete Application Assignment exist; page silent on group-to-app-role | Crosswalk | verified | Spoke, Application Management |
| 17 | OneDrive pre-provisioning needs SharePoint Administrator | Crosswalk | verified | MS Learn "Pre-provision OneDrive for users in your organization"; footnote added |
| 18 | ImmutableID hard-match repair through AD `mS-DS-ConsistencyGuid` | Crosswalk | verified | MS Learn "Configure Microsoft Entra Connect for an existing tenant", hard match vs soft match; footnote added |
| 19 | Admin Consent, Conditional Access not covered by spoke | Crosswalk | verified | Spoke action lists (no consent or CA action) |
| 20 | "Service principal actions exist" | Crosswalk | corrected | The Service Principal Management category has look-up actions only, and there's no directory-role action. Wording made precise |
| 21 | Tier and Execution columns (A0–A3/OOS, Identity Eng, escalate) | Crosswalk | restated-as-design | Program authority model |
| 22 | Formerly the Microsoft Azure Active Directory spoke; prebuilt Integration Hub spoke | What the spoke ships | verified | Spoke page ("formerly known as Microsoft Azure Active Directory spoke") |
| 23 | Ten action categories | What the spoke ships | verified | Spoke page category headings |
| 24 | Sample flows and subflows to clone | What the spoke ships | verified | Spoke page (User Onboarding/Offboarding flows; Add User to Group subflow) |
| 25 | Requires Integration Hub subscription | What the spoke ships; Coverage callout | verified | Spoke page |
| 26 | Custom app, OAuth 2.0; delegated + authorization code, application + client credentials | What the spoke ships | verified | Spoke page |
| 27 | Separate Microsoft Active Directory spoke for on-premises | What the spoke ships | verified | ServiceNow "Microsoft Active Directory Spoke" (Zurich). It also requires Integration Hub and a MID Server, added with a footnote |
| 28 | Reset Password accepts application `User-PasswordProfile.ReadWrite.All`; Change Password and Revoke User SignIn Sessions delegated (work or school) only | Two limits | verified | Spoke permission tables |
| 29 | "Not supported" entries are for personal Microsoft accounts | Two limits | verified | Spoke permission tables (Delegated, personal Microsoft account) |
| 30 | v1.5 history parenthetical | Two limits | corrected | History aside removed; the personal-accounts note kept |
| 31 | Coverage is release-dependent; validate against installed spoke | Coverage callout | restated-as-design | Operational advice |
| 32 | Each action needs matching Graph permission and admin consent | Coverage callout | corrected (citation) | `[^ms-graph]` cited the Entra built-in roles page, which is about directory roles, not Graph permissions. It now cites the MS Learn "Microsoft Graph permissions reference" (AdminConsentRequired column) and the spoke page's permission tables |
| 33 | Without Integration Hub, Spoke cells become manual | Coverage callout | restated-as-design | Follows from claim 25 |
| 34 | `-RedirectMessageTo` redirects; `-BlindCopyTo` adds Bcc (original still delivered) | Mechanism A | verified | MS Learn New-TransportRule, parameter text |
| 35 | `-Mode Audit` writes would-be actions to message tracking log, no delivery effect; Enforce | Mechanism A; code block | verified | MS Learn New-TransportRule `-Mode` (Enforce is the default) |
| 36 | `-SentTo` condition; code block parameters exist | Code block | verified | MS Learn New-TransportRule |
| 37 | "*New*-type Inbound Email Action" | Mechanism A | corrected | ServiceNow classifies incoming mail as new, reply or forward, and the action types are record action and email reply. Reworded to "an Inbound Email Action for mail ServiceNow classifies as *new*" with `[^sn-iea]`. Config table label changed to "(new email)". The figure caption is unchanged (images not edited) and still says "New-type" |
| 38 | Inbound email action creates the record (no watermark → new record) | Mechanism A | verified | ServiceNow Inbound email actions (Yokohama): with no watermark the action creates a record; a watermark match updates the existing one |
| 39 | Email Filters drop loops/junk | Figure; config table | verified | ServiceNow Email filters: Mark as Ignored / Move to Junk; defaults include "Junk email - sender equals recipient" and "Move spam to junk folder" |
| 40 | Reroute Business Rule for tickets assigned to Cloud Services | Mechanism A; config table | restated-as-design | Program design (inbound actions "function similarly to business rules", per ServiceNow) |
| 41 | `@microsoft.com` mail forced to A3, escalate-only | Triage | restated-as-design | Program rule |
| 42 | Microsoft sends from several addresses | Triage | verified | MS Learn "Email notifications in PIM" (`MSSecurity-noreply@microsoft.com`); Entra ops guide (`o365mc@email2.microsoft.com`, `azure-noreply@microsoft.com`); footnote added |
| 43 | Proof is the matching event in the Entra audit log | Triage | restated-as-design | Program rule |
| 44 | Six-step fixed triage order | Triage | restated-as-design | Program design; "(design guidance)" added inline |
| 45 | Manager approval then execute; SCTASK otherwise | ServiceNow pipeline | restated-as-design | Program design |
| 46 | Approval due date auto-approves, rejects or cancels | ServiceNow pipeline | verified | ServiceNow "Ask for Approval action" (Yokohama) |
| 47 | Due-date outcome reject or cancel, never approve | ServiceNow pipeline | restated-as-design | Program rule; "(design guidance)" added inline |
| 48 | `[^sn-fd]` cited a ServiceNow Community article | Footnote; references | corrected (citation) | Replaced with the primary ServiceNow docs "Ask for Approval action" page (the community page still resolves but isn't primary) |
| 49 | SAM pipeline; Admin Consent never auto-executes | SAM pipeline | restated-as-design | Program design |
| 50 | Scattered Spider posed as employees to get help desks to reset passwords / move MFA; advisory revised July 29, 2025 | Verify the person | verified | CISA AA23-320A ("Last Revised" July 29, 2025) |
| 51 | Verification ladder (accept phishing-resistant sign-in or re-proof; never email, caller ID, etc.) | Verify the person | restated-as-design | Program design; full ladder sourced in the Administrative Responsibilities Guide |
| 52 | Flow-definition table, create/modify steps | Describe/modify/create | restated-as-design | Program design |
| 53 | SLA example (3 business days) | Flow table | restated-as-design | Example value |
| 54 | Worked example (Payroll app, A2 → SAM; custom app-assignment role) | Worked example | restated-as-design | Program design |
| 55 | Configuration reference table | Config reference | restated-as-design | Program design (components verified in 34–40) |
| 56 | Companion kit release `helpdesk-entra-kit-v1.6`; not validated against a live tenant | Companion kit callout | restated-as-design | Kit metadata |
| 57 | Reference: Inbound email actions (Yokohama) URL resolves | References | verified | Page loads (Yokohama, updated Jan 30, 2025) |
| 58 | Reference: Email filters URL resolves | References | verified | Page loads |
| 59 | Reference: Entra ID spoke (Zurich) URL resolves | References | verified | Page loads |
| 60 | Reference: Microsoft Entra built-in roles URL | References | verified | 200, "Microsoft Entra Built-in Roles" |
| 61 | Reference: Least privileged roles by task URL | References | verified | 200, "Least privileged roles by task" |
| 62 | Reference: New-TransportRule URL | References | verified | 200, "New-TransportRule (ExchangePowerShell)" |
| 63 | Reference: PIM for Groups URL | References | verified | 200, "Privileged Identity Management (PIM) for Groups" |
| 64 | Reference: What is PIM? URL | References | verified | 200, "What is Privileged Identity Management?" |
| 65 | Reference: Enable SSPR tutorial URL | References | verified | 200, "Enable Microsoft Entra self-service password reset" |
| 66 | Footnote `[^ms-writeback]` URLs resolve | Footnotes | verified | Both 200. The writeback page's browser title is now "On-premises password writeback with self-service password reset", and its H1 still matches the cited title |

## Totals

verified 40 · corrected 7 · restated-as-design 19 · couldn't-verify 0

(Rows 32 and 48 are citation corrections. Row 30 removes a history aside.)

## Corrections that change meaning

- **Spoke quotation (claim 3).** The text was a quoted sentence that isn't on ServiceNow's spoke page. It is now the page's actual sentence, "provides actions to automate Entra tasks when events occur in ServiceNow", followed by the ten categories as a paraphrase. Source: ServiceNow Microsoft Entra ID spoke (Zurich).
- **Sign-in / audit-log row (claim 8).** "Audit log actions … Spoke (read-only)" → "Look up Sign Ins Stream — the only audit-logs action; no directory-audit action … Spoke for sign-ins (read-only); directory audit log manual". Source: same page, Audit Logs category.
- **Service principal row (claim 20).** "Service principal actions exist; governance keeps them manual" → "Service principal look-up actions only; no directory-role action". Source: same page, Service Principal Management category.
- **Inbound Email Action type (claim 37).** "*New*-type Inbound Email Action" → "an Inbound Email Action for mail ServiceNow classifies as *new* (no watermark, reply or forward marker)". Source: ServiceNow Inbound email actions (Yokohama).
- **Approval due date (claims 46–48).** The text now says the platform can auto-approve, reject or cancel at the due date, and that choosing reject or cancel is design guidance. The citation moved from a Community article to ServiceNow docs "Ask for Approval action".
- **Graph-permission citation (claim 32).** Moved from the Entra built-in roles page to the Microsoft Graph permissions reference.

## Couldn't verify

None. Two editor notes, both since applied: the heading now reads "The five recommendations" (it sits over a five-item list), and the email-intake figure caption now says "an Inbound Email Action for new mail".
