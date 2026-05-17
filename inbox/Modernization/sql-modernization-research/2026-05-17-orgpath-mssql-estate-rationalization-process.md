---
title: "OrgPath/OrgTree-Driven MS SQL Estate Rationalization Process"
doc-type: research-draft
status: DRAFT
audience: ["governance-steward", "data-engineer", "identity-engineer", "modernization-program-lead"]
classification: Controlled
boundary: GCC-Moderate
owner: "Michael Stratton"
created_at: "2026-05-17"
canon-source: "inbox/Modernization/sql-modernization-research/ (research artifact — not canon)"
companion-to: "2026-05-17-sql-modernization-strategy-expansion.md"
anchors:
  - "src/uiao/modernization/directory-migration/adapters/sql-server/sql-server-adapter-interface.md"
  - "src/uiao/adapters/modernization/active_directory/survey.py"
  - "src/uiao/canon/specs/Spec3-D1.1-Get-ServiceAccountScan.md"
  - "src/uiao/canon/UIAO_007_OrgTree_Modernization_AD_to_EntraID_v1.0.md"
  - "src/uiao/canon/UIAO_135_identity-directory-transformation-inventory.md"
  - "src/uiao/canon/UIAO_151_OrgPath_Codebook.md"
  - "docs/customer-documents/orgpath-narrative/07a-uiao-beneath-the-azure-ssot-stack.qmd"
  - "src/uiao/canon/charter/CHARTER-003.md"
proposed-canon-actions:
  - "UIAO_NNN — MS SQL Estate Rationalization Process (operator-facing spec)"
  - "ADR-NNN — DRIFT-SSOT-CONTENTION drift class"
  - "DM_090 §amend — extend inventory from instance-level to database/schema/table/row-count"
  - "uiao mssql rationalize CLI sub-app (discover, overlap, ssot, target, merge)"
  - "Reference-data overlap library (canon-seeded heuristic patterns)"
---

# OrgPath/OrgTree-Driven MS SQL Estate Rationalization Process

> **Status.** Draft research artifact under `inbox/` (not canon). Companion
> to `2026-05-17-sql-modernization-strategy-expansion.md` in the same
> directory. The strategy paper argues for a single canonical core
> operating database for the substrate's own state; this paper specifies
> the process the substrate runs *against the agency's MS SQL Server
> estate* to discover, evaluate, and consolidate.
>
> **Scope.** A repeatable five-phase pipeline — Discover → Detect
> Overlap → Designate SSOT → Select Efficient Target → Merge — driven by
> OrgPath/OrgTree as the join key. The process is **product-neutral**:
> it scores candidate consolidation targets against the operating-store
> contract (§5) without picking a specific product. Tenants choose
> based on existing ELAs, regulatory boundary, and operational profile.
>
> **What this process is NOT.** It is not a substitute for the existing
> DM_090 SQL Server Workload Adapter Interface — DM_090 handles the
> per-instance migration mechanics (SPN re-registration, service-account
> migration, Kerberos delegation preservation). This process *consumes*
> DM_090's outputs and adds the cross-instance overlap analysis,
> SSOT designation, and consolidation orchestration layers that DM_090
> explicitly leaves out.
>
> **Doctrine choices baked in.**
> - Overlap detection: **strict + semantic heuristics** (governance
>   call recorded in this artifact's authoring session).
> - SSOT granularity: **per data domain** (HR, Finance, Procurement,
>   Logistics, FOIA, etc.), not per table.

## 0. Executive Summary

The agency MS SQL estate is the canonical example of stacked persistence
the strategy paper warns about — every regional office, every project,
every retired-but-still-running line-of-business app has accreted its
own SQL instance, often with its own copy of the same reference data,
its own approximation of the same domain schema, and its own
service-account lineage that nobody fully owns. UIAO already governs
the *per-instance* modernization mechanics via DM_090. What's missing
is the *cross-instance* rationalization — the process that asks "given
twelve SQL instances all owning some flavor of Employee data, which
one is authoritative, which ones become caches, which ones get
retired?" — and answers it deterministically.

This document specifies that process. Five phases, each anchored to
existing canon where possible:

1. **Phase 1 — Estate Enumeration with OrgPath Attribution.** Extend
   DM_090's instance inventory to include the per-database, per-schema,
   per-table row-count and size profile. Every node in the resulting
   `mssql_estate` graph carries an OrgPath foreign key from the same
   `orgtree_node` table the strategy paper introduces in §6.
2. **Phase 2 — Overlap Detection.** Two-layer analysis: (a) strict
   schema-fingerprint and reference-data identity matching; (b)
   semantic heuristics for tables whose schemas differ but whose
   purpose is the same (name-similarity, FK-shape similarity,
   column-name-and-type Jaccard). Output: a per-data-domain overlap
   report ranking consolidation clusters by saved-instance count and
   data-volume reduction.
3. **Phase 3 — SSOT Designation.** Per data domain (HR, Finance,
   Procurement, etc.), nominate one authoritative instance based on
   six weighted criteria: population size, schema currency, OrgPath
   alignment, capacity headroom, boundary fit, downstream consumer
   count. Output: SSOT roster — one row per data domain with the
   designated authoritative instance, the demotion path for the
   others, and the cutover sequence. New drift class:
   `DRIFT-SSOT-CONTENTION` — fires when canon designates a domain SSOT
   that the live estate contradicts.
4. **Phase 4 — Efficient-Target Selection.** Per consolidation
   cluster, score candidate target products (Oracle, Azure SQL DB,
   SQL Server on Arc, Fabric SQL, PostgreSQL) against the
   operating-store contract from the strategy paper's amended §4.3.
   The process emits a scored shortlist; the tenant chooses. Canon
   names the scoring criteria, not the product.
5. **Phase 5 — Merge Playbook.** Per cluster: provision target → seed
   via Fabric mirror or vendor-native replication → wrap source
   endpoints in linked-server abstraction → cut over read traffic →
   cut over write traffic → validate against drift cycle →
   decommission source instances. Re-uses DM_090's SPN re-registration
   + service-account migration mechanics.

The contribution: a process that turns the "every agency has too many
SQL Servers" intuition into a deterministic, auditable, repeatable
program. The output is an SSOT roster that every downstream
consumer can join against and a consolidation backlog every
modernization program can execute against — both anchored by OrgPath.

## 1. Scope and Inputs

### 1.1 In scope

- Microsoft SQL Server instances reachable from the AD survey
  (`MSSQLSvc/*` SPN registration) on agency-governed networks.
- Azure Arc-enrolled SQL Server instances (per DM_090 Registered
  Implementations table).
- Azure SQL Managed Instance and Azure SQL Database instances
  governed by the tenant subscription (discovered via Azure Resource
  Graph rather than AD).
- Cross-instance analysis of databases, schemas, tables, reference
  data, and stewardship.

### 1.2 Out of scope

- Per-instance Kerberos/SPN migration mechanics — governed by DM_090.
- Per-row data-quality scoring inside an instance — governed by HR
  data quality spec (Spec2-D1.8) and equivalent per-domain quality
  specs for non-HR data.
- The substrate's own operating store — governed by the strategy
  paper (companion document) and the future ADR-074. This process
  governs the *agency's* SQL estate.
- Non-Microsoft databases. Oracle, PostgreSQL, MySQL, MariaDB,
  IBM Db2 instances are real and require equivalent
  rationalization, but each has its own discovery surface (no
  `MSSQLSvc/*` SPN equivalent) and warrants a sibling specification.
  This document is the MS SQL reference; sibling specs follow the
  same five-phase shape with vendor-specific discovery adapters.
- Embedded / file-based stores (SQLite, Access MDBs, Jet) — too
  numerous and operationally too low-value per instance to be
  governance-tracked. Drift here is handled at the application layer.

### 1.3 Inputs the process consumes

| Input | Source | Format | Authoritative for |
|---|---|---|---|
| SPN inventory | `src/uiao/adapters/modernization/active_directory/survey.py::extract_spn_inventory()` | JSON list of `{spn, principal, host, port}` | Kerberos-registered instance count and OrgPath-attribution candidate |
| Service account scan | Spec3-D1.1, [UIAO_139](../../../src/uiao/canon/specs/Spec3-D1.1-Get-ServiceAccountScan.md) | JSON list of `{account, sids, group_membership, kerberos_delegation}` | Owning-principal resolution for each instance |
| SQL Server auth audit | Spec3-D1.8 (referenced by ADR-068 and UIAO_135 §3.2) | JSON list of `{instance, auth_mode, protocols, always_on_state}` | Authentication-mode inventory (Windows / SQL / mixed); migration eligibility |
| Linked server inventory | Per-instance query against `sys.servers` (emitted by DM_090's discovery extension defined in §2 below) | JSON list of `{source_instance, target_instance, security_mode}` | Cross-instance dependency graph; cutover sequencing |
| OrgPath codebook | `src/uiao/canon/data/orgpath/codebook.yaml` (UIAO_151) | YAML | Domain hierarchy for attribution and grouping |
| Tenant Azure Resource Graph | Azure Resource Manager API via `uiao.adapters.entra_adapter` extensions | JSON | Azure SQL MI / DB inventory and ARM-tag-attributed OrgPath |
| Dependent-consumer inventory | Application catalog + connection-string scan (sibling spec to be added) | JSON | Downstream-consumer count used in SSOT scoring |
| Purview data map | `uiao_orgpath` custom metadata field per asset (OrgPath narrative ch.07a) | JSON via Purview Scan API | Sensitivity classification + lineage for prioritization |

Every input is already canon-attributable; the only new input is the
linked-server inventory (Phase 1's principal extension to DM_090).

### 1.4 Outputs the process produces

| Output | Consumed by | Persistence target |
|---|---|---|
| `mssql_estate` graph (instances, databases, schemas, tables, row-counts, sizes, OrgPath) | Phase 2 overlap analysis; consumed by the data-lake projection (UIAO_109 v2.0) | Core operating DB (per strategy paper) |
| Overlap report (per data domain) | Phase 3 SSOT designation; operator review surface | Markdown report + JSON sidecar |
| SSOT roster (one row per data domain) | Phase 4 target selection; downstream consumers; drift engine | Core operating DB; published as OSCAL-compatible artifact for audit |
| Target-selection scoring matrix (per consolidation cluster) | Operator decision; tenant procurement | Markdown report + JSON sidecar |
| Migration backlog (per cluster) | DM_090 execution; modernization program ticket queue | Core operating DB; emitted as work items to ITSM (ServiceNow per existing adapter) |
| Drift findings (`DRIFT-SSOT-CONTENTION`) | Substrate walker; governance dashboard | Same as all other drift classes |

The outputs are deliberately layered: the `mssql_estate` graph is the
raw fact base; the overlap report is the analytic layer; the SSOT
roster is the governance ratification; the target-selection matrix and
migration backlog are the operational outputs. Each layer is
auditable independently.

## 2. Phase 1 — Estate Enumeration with OrgPath Attribution

### 2.1 What DM_090 already produces

DM_090 §"Discovery Phase Requirements" specifies (paraphrasing):

- Forest-wide SPN enumeration for `MSSQLSvc/*`.
- Service-account inventory for SPN owners.
- Instance enumeration including named instances and port-only bindings.
- Kerberos delegation inventory.
- Linked-server inventory between SQL instances.
- Reporting Services / Analysis Services delegation chains.
- OrgPath attribution for each instance via service-account principal
  (preferred) or hosting computer (fallback); unattributed instances
  emit `DRIFT-IDENTITY` P2.

That covers the per-instance fact base. What it does not cover is the
*inside-the-instance* inventory — databases, schemas, tables,
row-counts, sizes — which the cross-instance overlap analysis
fundamentally depends on.

### 2.2 Extension required for Phase 2

The DM_090 discovery extension adds per-instance queries against the
SQL Server system catalogs. The queries are read-only, run under a
governance-scoped account with `VIEW SERVER STATE` + `VIEW ANY
DEFINITION` rights, and emit the following structured output:

```sql
-- Databases on each instance
SELECT name, database_id, create_date, compatibility_level,
       collation_name, state_desc, recovery_model_desc,
       (SELECT SUM(size) * 8 / 1024 FROM sys.master_files
        WHERE database_id = d.database_id) AS size_mb
FROM sys.databases d
WHERE database_id > 4;  -- exclude system DBs

-- Schemas per database
SELECT DB_NAME() AS database_name, name AS schema_name,
       principal_id
FROM sys.schemas
WHERE schema_id > 4;  -- exclude built-in

-- Tables per schema (with row counts and storage)
SELECT s.name AS schema_name, t.name AS table_name,
       p.rows AS row_count,
       SUM(a.total_pages) * 8 AS total_kb,
       SUM(a.used_pages) * 8 AS used_kb,
       t.create_date, t.modify_date
FROM sys.tables t
JOIN sys.schemas s ON t.schema_id = s.schema_id
JOIN sys.partitions p ON p.object_id = t.object_id
JOIN sys.allocation_units a ON p.partition_id = a.container_id
WHERE p.index_id IN (0, 1)
GROUP BY s.name, t.name, p.rows, t.create_date, t.modify_date;

-- Columns per table (for fingerprinting and semantic comparison)
SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME,
       DATA_TYPE, CHARACTER_MAXIMUM_LENGTH,
       NUMERIC_PRECISION, NUMERIC_SCALE,
       IS_NULLABLE
FROM INFORMATION_SCHEMA.COLUMNS
ORDER BY TABLE_SCHEMA, TABLE_NAME, ORDINAL_POSITION;

-- Foreign keys per table (for FK-shape comparison in Phase 2)
SELECT fk.name AS fk_name,
       OBJECT_SCHEMA_NAME(fk.parent_object_id) AS parent_schema,
       OBJECT_NAME(fk.parent_object_id) AS parent_table,
       OBJECT_SCHEMA_NAME(fk.referenced_object_id) AS referenced_schema,
       OBJECT_NAME(fk.referenced_object_id) AS referenced_table
FROM sys.foreign_keys fk;
```

The queries are emitted by DM_090's discovery extension as a single
governance-tagged batch per instance. Output is JSON, anchored to
the OrgPath value of the owning instance via the existing DM_090
attribution path.

### 2.3 OrgPath attribution per level

Every node in the resulting graph carries an OrgPath. Attribution
rules cascade:

| Level | OrgPath source | Fallback |
|---|---|---|
| **Instance** | Service-account principal's `extensionAttribute1` (per ADR-063) | Hosting computer's `extensionAttribute1`; if both absent, `ORG-BRANCH-UNPOSITIONED` |
| **Database** | Database owner principal's OrgPath (typically inherited from instance owner unless explicitly delegated) | Instance OrgPath |
| **Schema** | Schema owner principal's OrgPath (`AUTHORIZATION` clause) | Database OrgPath |
| **Table / View / SP** | Schema OrgPath (tables inherit from schema; not directly attributed unless explicit) | Schema OrgPath |

The cascade is recorded in the `mssql_estate` graph so that any node
can be queried for its effective OrgPath without re-walking. A node
whose OrgPath resolves to `ORG-BRANCH-UNPOSITIONED` is a `DRIFT-IDENTITY`
finding by definition; remediation precedes any overlap analysis on
that node.

### 2.4 Output: the `mssql_estate` graph

The Phase 1 output is a relational graph with five entity types and
their relationships:

```
mssql_instance (PK: instance_id)
  - host, port, version, edition, auth_mode, orgpath, attribution_source
  ↓ 1..N
mssql_database (PK: database_id, FK: instance_id)
  - name, compatibility_level, collation, size_mb, recovery_model, orgpath
  ↓ 1..N
mssql_schema (PK: schema_id, FK: database_id)
  - name, owner_principal, orgpath
  ↓ 1..N
mssql_table (PK: table_id, FK: schema_id)
  - name, row_count, total_kb, used_kb, create_date, modify_date,
    schema_fingerprint_hash, semantic_fingerprint_hash, orgpath
  ↓ 1..N
mssql_column (PK: column_id, FK: table_id)
  - name, data_type, max_length, precision, scale, is_nullable,
    ordinal_position

mssql_foreign_key (FK: parent_table_id, FK: referenced_table_id)
mssql_linked_server (FK: source_instance_id, target_instance_dsn)
```

The two fingerprint columns on `mssql_table` are populated in Phase 2.

### 2.5 Idempotence and re-discovery

The phase is idempotent: re-running emits the same graph if the
estate is unchanged. Changes between runs are computed as diffs and
emitted as drift events:

- Instance added / removed → `DRIFT-IDENTITY` if new and unattributed
- Database created / dropped → audit event, no governance action
  unless cross-references break
- Table created / dropped / row-count changed beyond threshold →
  recalculate fingerprints, re-evaluate overlap candidacy

The default re-discovery cadence is weekly; manual triggers via
`uiao mssql rationalize discover` are supported.

