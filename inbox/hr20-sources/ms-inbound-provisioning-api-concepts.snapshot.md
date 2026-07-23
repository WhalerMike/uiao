# Snapshot: API-driven inbound provisioning concepts (Microsoft Entra ID)

> **Source:** https://learn.microsoft.com/en-us/entra/identity/app-provisioning/inbound-provisioning-api-concepts
> **Page updated_at:** 2026-02-05 (ms.date 2025-07-24) · **Snapshot retrieved:** 2026-07-23
> Point-in-time extraction for durable reference. The live page is authoritative.

With API-driven inbound provisioning, the Microsoft Entra provisioning service supports integration with **any** system of record (HR app, payroll app, spreadsheet, SQL tables — on-premises or cloud). Any automation tool can retrieve workforce data and ingest it into Entra ID; attribute mappings control processing/transformation. Once data is in Entra ID, joiner-mover-leaver processes are configured with Lifecycle Workflows.

## Supported scenarios

1. **IT teams importing HR data extracts** with any automation tool (PowerShell, Azure Logic Apps) from flat files / CSV / SQL staging tables.
2. **ISVs building direct integration** — native sync so HR-system changes flow into Entra ID and connected on-premises AD domains (real-time or end-of-day bulk).
3. **System integrators building custom HR connectors.**

In all scenarios the provisioning service handles identity-profile comparison, scoping, and rule-based attribute flow — the API client does NOT compute create/update/enable/disable operations; it just uploads source data as a SCIM bulk request.

## End-to-end flow

1. Admin configures an API-driven inbound provisioning app from the gallery.
2. Admin grants access permissions and shares the endpoint with the API developer.
3. API client reads identity data from the authoritative source.
4. Client POSTs to the provisioning **/bulkUpload** Graph API endpoint of the app.
5. Success returns **HTTP 202 Accepted**.
6. Provisioning service applies attribute mappings and provisions the user — into **on-premises AD (hybrid users)** or **Entra ID (cloud-only users)** depending on the configured app.
7. Client queries the **provisioning logs API** for per-record status; failed records can be retried in the next bulk request.

## Key facts

- Asynchronous Graph **/bulkUpload** endpoint per provisioning app; OAuth token required.
- Graph permissions: `SynchronizationData-User.Upload`, `SynchronizationData-User.Upload.OwnedBy` (ISVs), `ProvisioningLog.Read.All`.
- Accepts SCIM bulk request payloads; SCIM schema extensions allow any attribute.
- **Throttling:** max 40 API calls per 5-second window (HTTP 429 beyond). Tenant-level: **2,000 calls/24h under Entra ID P1/P2; 6,000 calls/24h under Entra ID Governance**. Optimize payloads to 50 operations per call.
- One endpoint per provisioning app; multiple data sources = multiple apps.
- Near-real-time processing; progress visible in provisioning logs (portal + API).

## License requirements

Available with **Entra ID P1, P2, and Entra ID Governance** licenses.

## API selection guidance (when to use /bulkUpload)

Use the **HR inbound bulk API (/bulkUpload)** when sourcing employee records from an authoritative HR source into member accounts in Entra ID or on-premises AD; lifecycle then driven by Lifecycle Workflows triggering on `employeeHireDate` (onboarding) and `employeeLeaveDateTime` (offboarding), with Temporary Access Pass for first sign-in. Alternatives: Create user API (ad-hoc), Create invitation (guests), accessPackageAssignmentRequest (entitlement-driven access).
