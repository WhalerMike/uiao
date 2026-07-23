# Snapshot: Configure Oracle HCM for automatic user provisioning (Microsoft Entra ID)

> **Source:** https://learn.microsoft.com/en-us/entra/identity/saas-apps/oracle-hcm-provisioning-tutorial
> **Page updated_at:** 2026-06-15 · **Snapshot retrieved:** 2026-07-23
> This is a point-in-time extraction of the page's technical content for durable reference. The live page is authoritative.

The Inbound Provisioning API allows you to create, update, and delete users in Microsoft Entra ID and on-premises Active Directory from an external source such as Oracle Fusion Cloud HCM. Scope: Oracle Fusion Cloud HCM only (PeopleSoft and Taleo are out of scope).

## Prerequisites

- Oracle HCM account with privileges to view/export HCM data and access the Oracle HCM REST APIs (referenced: Human Resources 24A, Applications Common 24A).
- Microsoft Entra ID tenant with minimum **Entra ID P1** / EMS E3 / Microsoft 365 E3 (enables API-driven provisioning).
- Hybrid users only: provisioning agent installed on a Windows server connected to the AD domain.
- Roles needed: Application Administrator + Hybrid Identity Administrator (gallery app + provisioning job).
- **Entra ID Governance license** required for Lifecycle Workflows.
- Azure subscription if using Azure Logic Apps.

## Integration overview — three sync scenarios

1. **Initial / full sync** — all worker data from Oracle HCM to Entra ID directly or to on-premises AD; typically at initial setup.
2. **Delta sync** — incremental changes since last sync (new/updated/deleted workers).
3. **Writeback** (optional) — user attribute changes in Entra ID (username, email, phone) sent back to Oracle HCM.

## Integration steps (summary table)

1. Determine which HCM attributes to provision; map Oracle HCM attributes to SCIM; define unique-ID generation and transformation rules.
2. Grant permissions to the inbound provisioning API (create an API client application).
3. Determine provisioning target: **cloud-only → Entra ID** (gallery app "API-driven provisioning to Microsoft Entra ID") or **hybrid → on-premises AD** (install provisioning agent, gallery app, map SCIM→AD, update Entra Connect Sync / cloud sync mappings).
4. Initial sync: CSV export → SCIM → API; validate matching (send 5–10 records first).
5. Delta syncs: CSV extracts or ATOM feed APIs.
6. Writeback via Oracle Fusion ERP gallery connector.
7. Recommended: configure Entra Lifecycle Workflows (JML automation; Governance license).

## Matching and scoping

- **Matching attribute pair (default): Oracle HCM Person Number ↔ Entra/AD employee ID (`employeeId`/`employeeID`).** Must be populated before full sync.
- Use scoping filters to skip stale HR records (e.g., decades-old employment history).

## Initial sync — CSV export options

- **HCM Extract tool** (primary bulk-retrieval tool; complex selection criteria, fast formula database items).
- **Oracle BI Publisher** (scheduled/ad-hoc reports in XML/CSV).
- **Oracle Integration Cloud (OIC)** with the Oracle HCM Adapter.

Transform CSV → SCIM via Microsoft-provided methods: **PowerShell script** (inbound-provisioning-api-powershell) or **Azure Logic Apps** (inbound-provisioning-api-logic-apps). Select **Start provisioning** in the Entra admin center before sending payloads.

## Delta syncs — three options

**Option 1 — Oracle ATOM feed APIs (real-time):** subscribe to the Employee workspace ATOM collections: `newhire`, `empassignment`, `empupdate`, `termination`, `cancelworkrelship`, `workrelshipupdate`. Turn on ATOM feeds immediately after initial sync (delay = lost changes). A **custom module** (hosted in OIC, or Azure Functions / Logic Apps / Data Factory) must handle: data validation, unique ID generation, sequencing of ATOM feeds, ATOM→SCIM conversion, error handling. Microsoft recommends an Oracle HCM partner or SI to build it.

- **Joiner:** read new-hire ATOM feed; ensure personal/contact/employment/job data in SCIM payload; optionally query Workers/Employees REST endpoints for more attributes. To trigger Lifecycle Workflows include custom SCIM attribute `urn:ietf:params:scim:schemas:extension:COMPANYNAME:1.0:User:HireDate` (from Oracle *EffectiveStartDate*).
- **Mover:** triggered by FT↔contractor conversion, assignment change, work-relationship change, transfer, promotion. Fetch new values from the "Changed Attributes" section of the ATOM response.
- **Leaver:** include custom SCIM attribute `urn:ietf:params:scim:schemas:extension:COMPANYAME:1.0:User:TermDate` (from Oracle *EffectiveDate*). [sic — "COMPANYAME" typo is in the source page]

**Option 2 — CSV extracts** (periodic; can send deltas only, or full scope and let the provisioning service compute changes).

**Option 3 — Oracle Integration Cloud** with the HCM Adapter.

## SCIM bulk request

Payload is a `urn:ietf:params:scim:api:messages:2.0:BulkRequest` with Operations of method POST to `/Users`, using core + enterprise user schemas; `externalId` = workers.PersonNumber; enterprise extension carries employeeNumber, division, department, manager. Sent to the Graph **/bulkUpload** endpoint of the provisioning job. Validate payloads with cURL or Graph Explorer before enabling.

## Writeback (optional)

Configure an outbound provisioning job using the **Oracle Fusion ERP** gallery connector against the Oracle HCM SCIM APIs (admin account able to invoke the HCM User update API). In attribute mappings select only the **Update** target-object action; test with Provision on Demand.

## Appendix worksheets (attribute mappings)

### Worksheet 1 — Oracle HCM export attributes
Mandatory: Person Number, Account Status (True for non-terminated), First Name, Last Name. Required by Lifecycle Workflows: Hire Date, Termination Date. Optional common: address fields, Department Name, Division, Company, Username, Job Code, Job Name, Email, Manager, phone numbers, Work Address.

### Worksheet 2 — Oracle HCM → SCIM
| Oracle HCM | SCIM |
| --- | --- |
| Person Number | ExternalId |
| Account Status | Active |
| Street Address / City / State / Postal Code / Country | addresses[type eq "work"].* |
| Department Name | ...enterprise:2.0:User:department |
| Division | ...enterprise:2.0:User:division |
| Company | ...enterprise:2.0:User:organization |
| Username | displayName |
| First / Last Name | name.givenName / name.familyName |
| Job Code | ...COMPANYNAME:1.0:User:JobCode |
| Job Name | title |
| Email Address | emails[type eq "work"].value |
| Manager | ...enterprise:2.0:User:manager |
| Mobile / Phone | phoneNumbers[type eq "mobile"/"work"].value |
| Work Address | addresses[type eq "work"].formatted |
| Hire Date | ...COMPANYNAME:1.0:User:HireDate |
| Termination Date | ...COMPANYAME:1.0:User:TermDate |

### Worksheet 3 — unique ID / transformation rules
`userPrincipalName` (mandatory), `SamAccountName` (on-prem AD only), `parentDistinguishedName` (on-prem AD only) — see "Plan cloud HR application to Microsoft Entra user provisioning."

### Worksheet 4 — SCIM → on-premises AD
ExternalId→employeeID; Active→accountDisabled; addresses→streetAddress/l/st/postalCode/co; department/division/organization→department/division/company; displayName→cn; givenName/familyName→givenName/sn; JobCode→extensionAttribute1; title→title; manager→manager; mobile/work phone→mobile/telephoneNumber; work formatted address→physicalDeliveryOfficeName; **HireDate→extensionAttribute2; TermDate→extensionAttribute3**. Unmapped SCIM extension attributes can use extensionAttributes 1–15 or an AD schema extension.

### Worksheet 5 — on-premises AD → Entra ID (via cloud sync / Entra Connect)
Notably: **extensionAttribute2 → employeeHireDate; extensionAttribute3 → employeeLeaveDateTime**; division→EmployeeOrgData.division; company→companyName; sn→surname; title→jobTitle.

### Worksheet 6 — SCIM → Entra ID (cloud-only target)
Same shape as Worksheet 5's targets, directly: ExternalId→employeeId; Active→accountEnabled; **HireDate→employeeHireDate; TermDate→employeeLeaveDateTime**; JobCode→extensionAttribute1. Custom SCIM attributes: see "Extend API-driven provisioning to sync custom attributes."
