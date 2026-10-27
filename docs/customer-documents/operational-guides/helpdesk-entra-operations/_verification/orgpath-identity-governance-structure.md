# Verification — OrgPath Identity Governance Structure (Governance Structure Brief)

Claim-by-claim pass over `orgpath-identity-governance-structure.qmd` (published in the kit zip as `Governance-Structure-Brief.docx`), October 27, 2026. Microsoft claims checked on Microsoft Learn through the Learn MCP fetch and search tools (admin consent workflow, grant tenant-wide admin consent, enterprise application ownership, entitlement management approval policy, group management, Graph permissions reference). SailPoint claims checked on documentation.sailpoint.com (Identity Security Cloud approval settings, SoD prevention, certifications, Microsoft Entra ID connector supported features; IdentityIQ ServiceNow Service Desk integration). ServiceNow claim checked on the Zurich Microsoft Entra ID spoke page. Federal claims checked on whitehouse.gov (M-19-17 PDF), fedramp.gov (AC control text, 2026 Key Security Indicators). URLs that a Modernization Workbook footnote verified are cited with that access date. No personal data sent anywhere. The OrgPath layers, approval chains, ownership rules, risk tiers, cadences and implementation steps are program design; a "Design guidance" callout was added above the Executive summary.

## Claims log

| # | Claim (short) | Where | Verdict | Source |
|---|---|---|---|---|
| 1 | Entra ID has no native mechanism for routing governance decisions through an organizational hierarchy; doesn't know the accountable approver | Executive summary | corrected: admin consent workflow routes to designated reviewers; entitlement management (ID Governance licensing) routes through up to three stages starting with the manager attribute; what Entra lacks is the owner/business-unit/risk-tier model | configure-admin-consent-workflow; entitlement-management-access-package-approval-policy (Oct 27, 2026); licensing-fundamentals (workbook, Oct 20, 2026) |
| 2 | Admin consent request surfaces to any Global Admin or delegated consent permission | Problem | corrected: lists the roles that can grant (GA, PRA, custom consent role; Cloud App / App Admin except Graph app roles) | grant-admin-consent, Prerequisites (Oct 27, 2026) |
| 3 | No native mechanism to require a defined approval chain for consent | Problem | corrected: workflow exists but is a single review step; reviewer designation doesn't grant approval rights; "multi-stage" now stated | configure-admin-consent-workflow (Oct 27, 2026) |
| 4 | One consent can grant access to the entirety of the M365 data estate | Problem | corrected: "every mailbox or every site" (Microsoft's own examples) | grant-admin-consent intro; Graph permissions reference `Mail.ReadWrite` (Oct 27, 2026) |
| 5 | OMB M-19-17 requires traceable access decisions | Audit trails | corrected: restated as what the memo requires (ICAM governance structure; processes to manage and revoke access) | M-19-17, May 21, 2019, whitehouse.gov PDF (Oct 27, 2026) |
| 6 | NIST SP 800-53 AC-2, AC-6 | Audit trails | verified and restated precisely (AC-2 e approvals by defined personnel or roles, j review; AC-6 least privilege) | fedramp.gov/2026 Access Control (Oct 27, 2026) |
| 7 | KSI-IAM-ELP "ensuring least privilege", KSI-IAM-AAM "automating account management", anchored on AC-2/AC-6 | Audit trails | verified (names, statements, related controls); scope corrected to "for cloud services under FedRAMP 20x" | fedramp.gov/2026/reference/key-security-indicators (Oct 27, 2026) |
| 8 | ELP and AAM are "continuously validated" | Consequential risks | corrected: ELP measures "persistently reviewed"; AAM automated lifecycle management | same |
| 9 | Requesters cannot initiate an Admin Consent request | Layer 1 | restated-as-design; footnote: Entra lets any user request when the workflow is on | configure-admin-consent-workflow |
| 10 | Entra groups have owners (Layer 2 mapping) | Layer 2 | verified | how-to-manage-groups (Oct 27, 2026) |
| 11 | Enterprise Application owner field records the Application Owner | Layer 3, mapping table | verified, with clarifying footnote: owners can manage SSO, provisioning, assignment and owners (App Admin rights scoped to the app) | overview-assign-app-owners (Oct 27, 2026) |
| 12 | Application Owner is always a person, never a group | Layer 3 | restated-as-design; consistent with platform (groups can't own enterprise apps) | overview-assign-app-owners |
| 13 | Backup owner required | Layer 3; Backup owner | restated-as-design; Microsoft recommends at least two owners | overview-assign-app-owners |
| 14 | Owner assignments visible in the admin portal and auditable via Microsoft Graph | Formal documentation | verified (owned-by filter; Graph ownerless-app listing) | overview-assign-app-owners |
| 15 | Layer 4 holds GA / PRA, ideally via PIM JIT | Layer 4 | restated-as-design (PIM JIT activation is platform behavior, verified in sibling guide) | help-desk-administrative-responsibilities.qmd (pim-how-to-change-default-settings footnote) |
| 16 | Admin Consent approval Layer 4 only, non-delegable | Policy control | restated-as-design | — |
| 17 | Consent request arrives by email or portal notification | Current state | verified (workflow emails designated reviewers) | configure-admin-consent-workflow |
| 18 | Group-based access through security or Microsoft 365 groups | Group-based access | verified | assign-user-or-group-access-portal (workbook b04 ch09, Oct 20, 2026) |
| 19 | SAM generates certification campaigns automatically on schedule | Quarterly reviews; certifications | corrected: "runs on a schedule"; footnote: in Identity Security Cloud a schedule generates the preview and an admin starts the campaign | SailPoint "Starting a Campaign" (Oct 27, 2026) |
| 20 | Revocation automatic for connected apps, ServiceNow task otherwise | Privilege drift; certifications | verified, with footnote: native fallback is a task to the source owner; ServiceNow routing needs a service desk integration | SailPoint "Understanding Certifications" (Oct 27, 2026) |
| 21 | Approver timeout escalates automatically to the next layer | SAM routing | corrected: escalates along the configured chain (ISC: reviewer's manager twice, then fallback approver); "next layer" marked design guidance | SailPoint ISC access request approval settings (Oct 27, 2026) |
| 22 | SoD conflicts automatically blocked and routed to the IGO | SAM routing | corrected: with SoD blocking configured, conflicting requests are cancelled; exception to IGO is a separate request (design guidance) | SailPoint "Preventing Policy Violations" (Oct 27, 2026) |
| 23 | SAM Entra ID connector provisions group-based access | SAM steps | verified (account group management) | SailPoint Microsoft Entra ID connector, Supported Features (Oct 27, 2026) |
| 24 | Privileged roles need manual action because they aren't managed through group membership | ServiceNow integration | corrected: connector can manage directory roles; keeping them manual is the agency's choice (design guidance) | same |
| 25 | SAM creates a ServiceNow RITM and completion is reported back | ServiceNow integration | verified (IdentityIQ ServiceNow Service Desk integration: `sc_req_item`, status fetched back) | SailPoint IdentityIQ SDIM Basic Configuration (Oct 27, 2026) |
| 26 | RITM carries full approval chain; Help Desk doesn't route; loop closed in SAM | ServiceNow integration | restated-as-design | — |
| 27 | Certification decisions recorded with timestamp, approver and rationale | Certifications | couldn't-verify (no SailPoint page read today states the stored fields) | — |
| 28 | ServiceNow approval workflows mirror the chain; SLA auto-escalation | Integration with ServiceNow | restated-as-design (configuration the agency builds) | — |
| 29 | Benefits: unjustified access revoked automatically; unconfirmed assignments auto-revoked | Benefits summary | corrected: automatic for connected apps, remediation task otherwise; ISC treats unsigned items as no decision | SailPoint "Understanding Certifications" |
| 30 | Entra ID Spoke quotation | ServiceNow automation alignment | corrected: quotation replaced with the page's sentence and its ten categories | ServiceNow Zurich Entra ID spoke (Oct 27, 2026) |
| 31 | Residual gaps: OneDrive, ImmutableID hard-match, Conditional Access | ServiceNow automation alignment | corrected: adds authentication-method resets (spoke has only Reset Password); ImmutableID repair attributed to Identity Engineering | same; implementation-path.md routing table |
| 32 | Four layers, roles, routing per risk tier, tiers 1–3, quarterly / semi-annual / annual cadences, implementation steps, benefits framing ("minutes rather than days", "eliminates the most common source") | Throughout | restated-as-design | — |
| 33 | Only Global Administrators can turn on the admin consent workflow (context for Layer 4) | Layer 4 | verified | configure-admin-consent-workflow |

## Totals

verified 11 · corrected 13 · restated-as-design 8 · couldn't-verify 1

Rows 7, 11 and 20 are counted as verified; row 7 also had its scope wording narrowed, and rows 11 and 20 gained clarifying footnotes without a change in meaning.

## Corrections that change meaning

- Executive summary: "contains no native mechanism for routing governance decisions through an organizational hierarchy" → Entra's governance features route on what the tenant holds (consent workflow reviewers; entitlement management manager-based, up to three stages, with ID Governance licensing); it lacks the agency's owner/business-unit/risk-tier model. Sources: configure-admin-consent-workflow; entitlement-management-access-package-approval-policy; licensing-fundamentals.
- Admin consent: "surfaces to any Global Admin or delegated consent permission … no mechanism for a defined approval chain" → named granting roles; the workflow is a single review step and reviewers need a granting role; no multi-stage chain. Sources: grant-admin-consent; configure-admin-consent-workflow.
- "Entirety of the Microsoft 365 data estate" → "every mailbox or every site". Source: grant-admin-consent.
- Federal paragraph: the three sources no longer "require traceable decisions" each; restated to what each requires, and FedRAMP 20x KSIs scoped to cloud services. Sources: M-19-17; FedRAMP AC; FedRAMP KSIs.
- "Continuously validated" → ELP "persistently reviewed", AAM automated lifecycle management. Source: FedRAMP KSIs.
- Escalation "to the next layer" → along SAM's configured escalation chain (next layer is design). Source: SailPoint ISC approval settings.
- SoD "blocked and routed to the IGO" → cancelled when SoD blocking is configured; exception is a separate request. Source: SailPoint "Preventing Policy Violations".
- Privileged roles "not managed through group membership" → kept out of automated provisioning by agency choice; the connector can manage directory roles. Source: SailPoint Entra ID connector Supported Features.
- Campaigns "generated automatically" → "run on a schedule", with the ISC preview/start caveat. Source: SailPoint "Starting a Campaign".
- Benefits table: automatic revocation → connector or remediation task. Source: SailPoint "Understanding Certifications".
- Spoke callout: quotation corrected to the page's wording; residual-gap list now includes authentication-method resets and moves ImmutableID to Identity Engineering. Source: ServiceNow Zurich Entra ID spoke.

## Couldn't verify

- Row 27: that SAM records each certification decision with timestamp, approver and decision rationale. Left as written; the SailPoint pages read today don't list the stored fields.
- The ISC SDIM equivalent: the RITM row was verified on the IdentityIQ ServiceNow Service Desk page; an Identity Security Cloud page describing RITM creation wasn't found. The text doesn't name the SailPoint product, so it stands.
