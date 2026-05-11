---
document_id: DM_090
title: "SQL Server Workload Adapter Interface"
version: "0.1-draft"
status: DRAFT
owner: "Michael Stratton"
created_at: "2026-05-11"
updated_at: "2026-05-11"
boundary: GCC-Moderate
core_concepts: ["#1 SSOT", "#3 Identity as root namespace", "#5 Certificate-anchored overlay"]
priority: HIGH
risk: "Silent Kerberos failure post-migration; SQL sprawl into ungoverned data plane"
---

# SQL Server Workload Adapter Interface

**Priority:** HIGH | **Risk:** Silent Kerberos failure post-migration; SQL sprawl into ungoverned data plane

SQL Server is governed as a workload, not just as a data source. The
adapter coordinates four cross-cutting concerns that the rest of the
directory-migration canon already covers in isolation: SPN registration
(LDAP-proxy / Kerberos surface), service account lifecycle (sync-engine
+ orgtree workload identity), certificate-based authentication (PKI),
and the data-plane bridge into the Azure SSOT stack (OneLake mirroring
+ Purview registration per the OrgPath Narrative chapter 07a).

## Registered Implementations

| Adapter | Use Case |
|---|---|
| `mssql-onprem/` | On-premises SQL Server (Standard, Enterprise, Developer; 2016+) |
| `azure-arc-sql/` | Azure Arc-enrolled SQL Server (hybrid management plane) |
| `azure-sql-mi/` | Azure SQL Managed Instance |
| `azure-sql-db/` | Azure SQL Database (single database and elastic pool) |
| `fabric-sql/` | Microsoft Fabric SQL endpoint (post-mirroring) |

## Discovery Phase Requirements (Phase 1 — before any migration)

- Forest-wide SPN enumeration for `MSSQLSvc/*` prefixes (see
  [`src/uiao/adapters/modernization/active_directory/survey.py`](../../../../adapters/modernization/active_directory/survey.py)
  `extract_spn_inventory()`; emits the `spn_inventory` artifact defined
  in
  [`src/uiao/schemas/orgtree-readiness/orgtree-readiness.schema.json`](../../../../schemas/orgtree-readiness/orgtree-readiness.schema.json)
  `#/definitions/spnInventory`)
- Service account inventory for the principals owning the SPNs (Spec3-D1.1, [`UIAO_139`](../../../../canon/specs/Spec3-D1.1-Get-ServiceAccountScan.md))
- Instance enumeration including named instances and port-only bindings;
  `dbatools` `Find-DbaInstance` is the supported supplementary tool
- Kerberos delegation chain inventory — unconstrained, constrained, and
  resource-based; cross-referenced with PKI adapter findings for ADCS-
  dependent SPN patterns
- Linked-server inventory between SQL instances (each linked server
  carries its own Kerberos delegation requirement)
- Reporting Services and Analysis Services delegation chains
- OrgPath attribution for each instance via the service-account
  principal (preferred) or hosting computer (fallback). Unattributed
  instances emit a `DRIFT-IDENTITY` finding with severity P2 and must
  be remediated before migration begins.

## Required Capabilities

- Service-account migration without breaking the SPN registration
  (re-registration against the migrated principal must be a recorded
  provenance event, not a side-effect)
- Kerberos delegation chain preservation across the migration boundary
- Certificate-based authentication for SQL service-broker, encrypted
  endpoints, and Always Encrypted column master keys — coordinated with
  the [PKI adapter](../pki/pki-adapter-interface.md)
- Side-by-side operation during the migration window: legacy SQL
  instances stay operational; OneLake mirroring or shortcuts surface the
  data in the Fabric workspace governed by the matching Fabric Domain
  (per OrgPath Narrative chapter 07a)
- Purview data-map registration with `uiao_orgpath` custom metadata so
  the asset's organizational attribution is queryable in the data plane
- Optional Azure Arc registration as the post-migration verification
  surface for instances that remain on-premises

## Migration Sequence

1. Enumerate SPN inventory with phase tag `pre_migration` (`survey.py`
   `extract_spn_inventory(phase="pre_migration")`)
2. Resolve every SPN to an owning OrgPath via the principal or hosting
   computer; emit and remediate `DRIFT-IDENTITY` findings for
   unattributed instances before continuing
3. Provision migrated principals (managed identity, gMSA, or domain
   account in the target tenant) for each SQL instance
4. Re-register SPNs against the migrated principals; record the
   transition in the substrate provenance chain so a downstream
   `DRIFT-AUTHZ` check can confirm the owner change was authorized
5. Validate Kerberos authentication end-to-end against the migrated
   principal, including linked-server chains and Reporting Services
   delegation
6. Re-run SPN inventory with phase tag `post_migration`; the substrate's
   drift comparison (see [`docs/docs/16_DriftDetectionStandard.qmd` §7.1](../../../../../../docs/docs/16_DriftDetectionStandard.qmd))
   surfaces the four SPN-drift conditions; remediate before cutover
7. Optionally mirror the instance into OneLake under the Fabric Domain
   matching the owning OrgPath; register the resulting asset in Purview
   with the `uiao_orgpath` custom metadata field for adaptive-policy
   scoping per [OrgPath Narrative chapter 07a](../../../../../../docs/customer-documents/orgpath-narrative/07a-uiao-beneath-the-azure-ssot-stack.qmd)
8. Decommission only after at least one full drift cycle confirms zero
   `DRIFT-IDENTITY` and zero `DRIFT-AUTHZ` SPN findings against the
   migrated state

## Drift Surface

SQL Server-specific drift conditions are catalogued in
[`docs/docs/16_DriftDetectionStandard.qmd` §7.1](../../../../../../docs/docs/16_DriftDetectionStandard.qmd).
Severity P1 conditions (SPN absent post-migration; SPN owner changed
without provenance) halt the deployment and alert; severity P2 conditions
auto-remediate when deterministic.

## Cross-References

- [`ldap-proxy/ldap-adapter-interface.md`](../ldap-proxy/ldap-adapter-interface.md) — Kerberos and LDAP surface this adapter inherits from
- [`pki/pki-adapter-interface.md`](../pki/pki-adapter-interface.md) — Certificate-based authentication coordination
- [`sync-engine/sync-adapter-interface.md`](../sync-engine/sync-adapter-interface.md) — Service-account lifecycle pipeline
- [`../../ad-dependency-inventory.md`](../../ad-dependency-inventory.md) — 11-object dependency inventory (SPNs row)
- [`../../../../adapters/modernization/active_directory/survey.py`](../../../../adapters/modernization/active_directory/survey.py) — `extract_spn_inventory()` implementation
- [`../../../../canon/specs/Spec3-D1.1-Get-ServiceAccountScan.md`](../../../../canon/specs/Spec3-D1.1-Get-ServiceAccountScan.md) — Service-account scan canonical contract
- [`../../../../../../docs/docs/16_DriftDetectionStandard.qmd`](../../../../../../docs/docs/16_DriftDetectionStandard.qmd) — Drift taxonomy and §7.1 SPN drift detection
- [`../../../../../../docs/customer-documents/orgpath-narrative/07a-uiao-beneath-the-azure-ssot-stack.qmd`](../../../../../../docs/customer-documents/orgpath-narrative/07a-uiao-beneath-the-azure-ssot-stack.qmd) — Azure SSOT stack bridge (Purview data-map + Fabric Domain assignment + OneLake mirroring)
- [`../../../../../../docs/customer-documents/whitepapers/federal-ssot-alignment.qmd`](../../../../../../docs/customer-documents/whitepapers/federal-ssot-alignment.qmd) — Federal mandate alignment over the identity layer
