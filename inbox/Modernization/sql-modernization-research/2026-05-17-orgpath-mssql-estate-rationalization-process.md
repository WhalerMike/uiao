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

## 3. Phase 2 — Overlap Detection

The analytic core of the process. Takes the Phase 1 `mssql_estate`
graph as input; produces per-data-domain overlap clusters as output.
Two-layer analysis: a strict layer that yields high-confidence
findings without operator review, and a semantic-heuristics layer
that yields candidate findings with confidence scores requiring
operator ratification.

### 3.1 Strict layer — exact identity matches

The strict layer requires no judgment calls. It surfaces only
mathematically-identical findings, suitable for automated
de-duplication.

**Schema fingerprint** — computed per table as a deterministic hash:

```
schema_fingerprint = SHA256(
  table_name                                     // normalized: lowercase, stripped
  || sorted_tuple_of (column_name, data_type, max_length, precision, scale, nullable, ordinal_position)
  || sorted_tuple_of (foreign_key_target_table, target_column)
  || primary_key_column_list
)
```

Two tables with the same `schema_fingerprint` have *structurally
identical* schemas — same columns in same types, same FK shape, same
PK shape. They are candidates to be the same logical entity. They
may or may not have the same *content*; that's a separate test.

The fingerprint is intentionally insensitive to:
- Index definitions (operational; not structural)
- Storage parameters (filegroups, partition schemes, compression)
- Identity seeds and check constraints (per-instance state)
- Trigger bodies (behavior, not structure)
- Default constraints (declarative metadata, not structure)

It is intentionally sensitive to:
- Column ordering (preserves the wire-protocol shape)
- Column names (semantically meaningful)
- Type widths (semantically meaningful)
- FK target relationships (preserves the entity graph)

**Reference-data overlap** — for well-known reference datasets, the
strict layer computes a row-content hash over a deterministic
serialization:

```
reference_data_hash = SHA256(
  table_name
  || sorted_rows( canonical_serialize(row_values) )
)
```

The reference-data overlap test runs only on tables whose row count
falls within a configurable window (default: 1 ≤ row_count ≤ 10000)
and whose schema fingerprint matches a known reference-data pattern
(seeded in Appendix A). Two tables with the same `reference_data_hash`
are structurally and content-identically the same dataset — strict
duplication, can be retired with no semantic ambiguity.

Examples of canon-seeded reference-data patterns:
- US state codes (50 + DC + territories)
- Country codes (ISO 3166-1 alpha-2 / alpha-3)
- Federal occupation series codes (OPM-defined)
- Federal pay-plan codes
- Currency codes (ISO 4217)
- Employment-status enumerations (Active / Separated / Retired / etc.)
- DoD service-component codes
- GS-grade enumerations

The reference-data library is canon, not adapter-private — agencies
extend it via the same PR + governance-review process used for any
other canon registry.

**Strict-layer outputs:**

| Finding | Trigger | Confidence | Auto-actionable |
|---|---|---|---|
| `IDENTICAL-SCHEMA` | Two or more tables share a `schema_fingerprint` | 100% | Yes — flagged as merge candidates |
| `IDENTICAL-REFERENCE-DATA` | Two or more tables share `reference_data_hash` within the reference-data pattern set | 100% | Yes — flagged for direct retirement |
| `SHADOW-CATALOG` | One instance's database name + schema fingerprint set is a subset of another instance's | 100% | Yes — strong consolidation candidate |

### 3.2 Semantic layer — heuristic similarity

The semantic layer addresses the common case where two systems serve
the same purpose but were built independently by different teams at
different times. Their schemas differ — sometimes substantially — but
the underlying *entity* is the same (e.g., two HR systems both
maintaining "employees" with different column names and types).

The semantic layer is intentionally **opinionated and tunable**.
Confidence scores are emitted; operators ratify before any
consolidation action.

**Three heuristic signals, combined into a composite score:**

#### 3.2.1 Name-similarity (table-level)

Token-based normalization of table names, then comparison:

1. **Normalize**: lowercase; strip schema prefix; tokenize on
   underscores / camelCase / common abbreviations (e.g.
   `tblEmployees` → `[employee]`; `HR_EmpAddr` → `[hr, employee, address]`;
   `tEmpHist_2019` → `[employee, history]` — discard year suffix).
2. **Apply domain dictionary**: canon-seeded expansion of common
   federal-IT abbreviations (`emp` → `employee`, `acct` → `account`,
   `dept` → `department`, `loc` → `location`, `addr` → `address`,
   `org` → `organization`, etc.).
3. **Compute similarity**: cosine similarity over token frequency
   vectors. Threshold default: ≥ 0.75 for "likely same entity."

The domain dictionary lives in canon — `canon/data/mssql-rationalization/
abbreviation-dictionary.yaml` — and is extended via PR like any other
canon data.

#### 3.2.2 FK-shape similarity (graph-level)

Each table's foreign-key graph is summarized as a structural
signature:

```
fk_signature = sorted_tuple_of (
  outbound_fk_count,
  inbound_fk_count,
  fk_target_table_signatures        // recursive, capped at depth 2
)
```

Two tables with similar FK signatures are likely playing the same
role in the entity graph. A standalone "addresses" table referenced
by two parent tables (`employee` and `vendor`) has a distinctive
FK shape that's hard to confuse with anything else.

Jaccard similarity over (signature, depth) sets. Threshold default:
≥ 0.6 for "likely structurally analogous."

#### 3.2.3 Column-set similarity (within-table)

Jaccard similarity over (normalized_column_name, data_family) pairs,
where data_family groups types:

| Family | Includes |
|---|---|
| `numeric_id` | `int`, `bigint`, `uniqueidentifier`, `numeric(N,0)` with N ≥ 10 |
| `short_text` | `varchar(N)` / `nvarchar(N)` with N ≤ 100 |
| `long_text` | `varchar(N)` / `nvarchar(N)` with N > 100; `text`, `ntext`, `varchar(MAX)` |
| `datetime` | `datetime`, `datetime2`, `smalldatetime`, `date`, `time`, `datetimeoffset` |
| `money` | `money`, `smallmoney`, `decimal` / `numeric` with non-zero scale |
| `binary` | `binary`, `varbinary`, `image` |
| `boolean` | `bit` |
| `xml_or_json` | `xml`, `json` (SQL Server 2022+) |
| `spatial` | `geography`, `geometry` |

The family taxonomy is deliberately broad — two tables that both
have a `varchar(50)` and a `nvarchar(40)` column called "name"
count as having a `(name, short_text)` pair in common, even though
the wire-protocol shape differs.

Column-name normalization uses the same domain dictionary as the
table-name heuristic. Threshold default: ≥ 0.5 for "likely
analogous columns."

#### 3.2.4 Composite score

Weighted combination:

```
semantic_overlap_score =
    0.40 * name_similarity_score
  + 0.25 * fk_shape_similarity_score
  + 0.35 * column_set_similarity_score
```

Weights are canon-tunable per agency (some agencies have very
disciplined naming → up-weight name; others have inherited
hand-written schemas → up-weight FK shape). The default weights
reflect the empirically common pattern in federal estates.

**Confidence bands:**

| Score range | Confidence band | Operator action |
|---|---|---|
| ≥ 0.85 | High | Auto-flag for consolidation review |
| 0.60–0.85 | Medium | Surface in overlap report; operator triage required |
| 0.35–0.60 | Low | Show only on request (full-detail mode) |
| < 0.35 | None | Not flagged |

### 3.3 Cross-instance density signals (no content access required)

Phase 1 produces three signals that operate purely on the topology
graph — useful when SQL-side content access is not yet authorized
(the Tier-A1 / read-only-AD-only scenario from the strategy paper's
read-only assessment patterns):

**Per-segment instance density.** For each OrgPath segment, count
the instances attributed to it. A segment hosting more instances
than peer segments of comparable population size is a
consolidation-opportunity signal even without content inspection.

```
density_outlier_score(segment) =
   instance_count(segment) /
   median_instance_count(siblings(segment))
```

Score ≥ 2.0 (twice the median) is flagged as a consolidation
opportunity. The finding is honest about its weakness — it doesn't
say *which* instances to merge, only that the segment is over-
represented.

**Service-account sprawl.** Service accounts owning more than
N (default: 5) instance SPNs are flagged as centralized-identity
candidates. The pattern indicates either: (a) a shared service
account managing multiple legitimate instances (operationally
acceptable but governance-weak), or (b) a service account that
inherited responsibility for instances during prior consolidations
and never had ownership re-delegated (governance-strong-anti-pattern).

**Zombie candidates.** Instances whose owning host's
`lastLogonTimestamp` is older than the configured threshold
(default: 90 days) are flagged for verification. A genuinely
retired host that still appears in AD as an SPN registration is a
governance leak — the SPN should be cleaned up. A still-running
host that hasn't authenticated to a DC in 90 days is unusual
enough to warrant manual confirmation.

These three signals are computed during the discovery walk; they
require nothing beyond AD read-only + the SPN inventory that
Phase 1 already produces.

### 3.4 Output — the overlap report

The Phase 2 output is a structured overlap report, partitioned by
**data domain** (per the SSOT-granularity choice ratified for this
artifact: HR, Finance, Procurement, Logistics, FOIA, etc. — see
Appendix B for the seed domain catalog).

Per-domain report structure:

```yaml
domain: HR
period_covered: 2026-05-01 .. 2026-05-15
phase: post-discovery + post-overlap
findings:
  strict:
    identical_schema:
      - cluster_id: hr-employees-001
        tables: [
          { instance: "FIN-DB-01\HRSYS", schema: dbo, table: Employees, row_count: 12450 },
          { instance: "OPS-DB-02\HRACCESS", schema: dbo, table: Employees, row_count: 12321 },
          { instance: "LEGACY-DB-04\HR", schema: dbo, table: tblEmpMaster, row_count: 10987 }
        ]
        confidence: 1.0
        notes: "Same schema_fingerprint; row counts diverge — likely partial/replicated copies"
    identical_reference_data:
      - cluster_id: hr-pay-plan-codes-002
        tables: [...]
        confidence: 1.0
    shadow_catalog:
      - cluster_id: hr-shadow-003
        parent_instance: "PROD-DB-01\HRMASTER"
        shadow_instances: ["DEV-DB-04\HR_COPY", "ARCHIVE-DB-09\HR_2020"]
        confidence: 1.0
  semantic:
    candidate_clusters:
      - cluster_id: hr-employees-semantic-004
        tables: [
          { instance: "FIN-DB-01\HRSYS", schema: dbo, table: Employees, semantic_overlap_score: 1.0 },
          { instance: "REGIONAL-DB-07\WEST", schema: dbo, table: EmpRecords, semantic_overlap_score: 0.87 },
          { instance: "LEGACY-DB-12\OLDHR", schema: dbo, table: HR_Master_View_2018, semantic_overlap_score: 0.81 }
        ]
        composite_signal_breakdown: { name: 0.91, fk_shape: 0.78, column: 0.92 }
        confidence_band: high
        operator_action: review
  topology:
    density_outliers: [...]
    service_account_sprawl: [...]
    zombie_candidates: [...]
opportunity_summary:
  consolidation_clusters_identified: 9
  instances_potentially_retired: 11
  estimated_data_reduction_gb: 3400
  open_governance_questions: 3
```

The report is the input to Phase 3 (SSOT designation). It is also
the artifact the modernization program presents to leadership when
justifying scope and ROI. The structured shape is canon-stable so
operators can compare reports across periods to track consolidation
progress.

### 3.5 Concurrency, performance, and freshness

Overlap analysis is `O(N²)` in the worst case (every table compared
to every other table within a domain). At federal scale this can
mean millions of comparisons. Three mitigations:

1. **Domain partitioning.** Comparisons happen *within* a data domain,
   not across the full estate. HR-domain tables are compared to other
   HR-domain tables; not to FIN-domain tables. Domain attribution is
   inferred from a combination of (a) schema-name pattern matches
   (e.g., `hr_*` schemas → HR domain), (b) FK reachability to known
   domain anchor tables, and (c) operator override. Cross-domain
   overlap is a separate, optional, full-scan analysis run quarterly.

2. **Hash-bucketed comparison.** Schema fingerprints partition tables
   into buckets; only tables in the same bucket are compared
   semantically. A 50,000-table estate may produce only ~500 buckets,
   each with average 100 tables — `100² = 10,000` comparisons per
   bucket, manageable.

3. **Sampling for row-content hashes.** The `reference_data_hash`
   computation reads every row, which is expensive for tables
   approaching the 10,000-row ceiling. Sampling — hash 10% of rows
   and accept a stable hash if 100% of three independent samples
   converge — reduces I/O by 90% with high probability of correctness.
   Conflicts trigger a full-table hash.

The Phase 2 SLA target: complete overlap analysis on a
1,000-instance, 100,000-table estate within 6 hours on a single
analyst workstation. Larger estates parallelize trivially by domain.

## 4. Phase 3 — SSOT Designation (per data domain)

For each data domain identified in the overlap report, nominate one
authoritative SQL instance. The other instances in the same domain
become caches, replicas, or retirees on a defined schedule.

SSOT granularity is **per data domain** (HR, Finance, Procurement,
etc.) — not per table. The coarser granularity matches federal
CDO governance shape (data stewardship is assigned at the domain
level by an executive owner; not at the per-table level) and avoids
the operator-overload of maintaining a roster of 50,000 individual
table-level designations.

### 4.1 The six scoring criteria

Each candidate instance is scored against six weighted criteria.
Weights are canon-tunable per agency; the defaults below reflect the
empirically common pattern in federal estates.

| Criterion | Weight | Signal | Source |
|---|---|---|---|
| **Population size** | 0.20 | Total row count for the domain's anchor tables on this instance vs. peers | Phase 1 `mssql_estate.row_count` |
| **Schema currency** | 0.15 | Recency of schema changes (newer = more actively maintained); also penalize abandoned schemas | `mssql_table.modify_date`, aggregated per instance |
| **OrgPath alignment** | 0.20 | Distance between the instance's OrgPath and the domain's canonical OrgPath segment | OrgPath cascade + domain catalog (Appendix B) |
| **Capacity headroom** | 0.10 | Storage and compute headroom on the host vs. current utilization | Phase 1 instance-level metrics + host capacity (read-only) |
| **Boundary fit** | 0.15 | Match between the instance's residence (cloud region, security boundary) and the domain's regulatory profile | OrgPath segment metadata + boundary registry (`gcc-boundary-gap-registry.yaml`) |
| **Downstream consumer count** | 0.20 | Number of distinct applications / consumers that already connect to this instance | Consumer inventory (sibling spec input from Phase 1 §1.3) |

**Composite SSOT-candidate score:**

```
ssot_score(instance, domain) =
    0.20 * normalize(population_size)
  + 0.15 * normalize(schema_currency)
  + 0.20 * normalize(orgpath_alignment)
  + 0.10 * normalize(capacity_headroom)
  + 0.15 * normalize(boundary_fit)
  + 0.20 * normalize(consumer_count)
```

Each criterion is normalized to [0, 1] across the candidate set per
domain. The highest-scoring instance is the nominee; ties are
broken by the criterion-weight order above (population size first,
then OrgPath alignment, etc.).

### 4.2 Candidate qualification (eligibility gate before scoring)

An instance qualifies as an SSOT candidate only if it satisfies the
following preconditions. Disqualified instances are still in the
domain but cannot be SSOT — they become replicas, caches, or
retirees.

| Precondition | Why |
|---|---|
| OrgPath is Active (not `ORG-BRANCH-UNPOSITIONED`, not retired) | Cannot designate an SSOT for a segment that no longer exists |
| Auth mode supports modernization sequencing per ADR-068 | SSOT must be on a CBA / Entra-auth-eligible path; SQL-Auth-only instances become caches at best |
| Instance is within the agency's authorization boundary | An instance outside the GCC-Moderate (or higher) boundary cannot be SSOT for in-boundary data |
| Last-modified within the staleness window (default: 365 days) | Stale instances become archives, not authorities |
| Operating system version supports current SQL Server major release (or migration path is funded) | EOL hosts cannot anchor SSOT — their host migration is a prerequisite |
| Service account satisfies workload-identity-federation contract (ADR-004) or has a documented migration plan | Centralized-identity smells (one service account hosting many instances) disqualify until split |

### 4.3 The SSOT roster

Phase 3 produces the **SSOT roster** — one row per data domain
declaring the authoritative instance, the demotion of peers, and the
cutover schedule.

```yaml
ssot_roster:
  - domain: HR
    canonical_orgpath: /CORP/US/HR
    authoritative_instance:
      identifier: "PROD-DB-01\\HRMASTER"
      ssot_score: 0.87
      score_breakdown:
        population_size: 0.92
        schema_currency: 0.78
        orgpath_alignment: 1.0
        capacity_headroom: 0.65
        boundary_fit: 1.0
        consumer_count: 0.81
      ratified_by: governance-steward
      ratified_at: "2026-05-20"
      ratification_evidence: PR-NNN
    demoted_instances:
      - identifier: "FIN-DB-01\\HRSYS"
        target_role: read-replica
        cutover_window: 2026-Q3
        migration_owner: hr-platform-team
      - identifier: "REGIONAL-DB-07\\WEST"
        target_role: cache  # synced from authoritative; not directly writable
        cutover_window: 2026-Q3
        migration_owner: regional-it-team
      - identifier: "LEGACY-DB-12\\OLDHR"
        target_role: retire
        retirement_window: 2026-Q4
        archival_target: cold-storage-fabric-archive
        migration_owner: modernization-pmo
    related_drift_findings:
      - drift_id: DRIFT-SSOT-CONTENTION-001
        observation: "REGIONAL-DB-07 currently asserts authority over EmpRecords; conflicts with canon SSOT"
        severity: P2
        remediation: see demotion plan above
```

The roster lives in canon (proposed location:
`src/uiao/canon/data/mssql-rationalization/ssot-roster.yaml`) and is
ratified by the governance steward via PR. Every row carries explicit
provenance — who ratified, when, evidence reference. A change to the
roster (re-designation of SSOT, change in target role) requires a
new PR and a new ratification line.

### 4.4 The `DRIFT-SSOT-CONTENTION` drift class (new)

A new drift sub-class proposed for inclusion in
`docs/docs/16_DriftDetectionStandard.qmd` and the UIAO-SSOT (UIAO_001)
drift baseline:

| Class | Trigger | Severity |
|---|---|---|
| `DRIFT-SSOT-CONTENTION` | A canonically-designated SSOT instance for a domain disagrees with the live estate in a way that indicates another instance is acting as authority. Concretely: a write originating from a demoted instance (not the canonical SSOT) that modifies a non-cache-eligible column; an instance whose OrgPath assignment changed without re-ratification of the roster; a downstream consumer reading from a cache when the authoritative SSOT is operationally reachable. | P2 by default; P1 if remediation window exceeded |

Detection mechanisms:
- **Write-origin analysis.** SQL Server Audit captures writes; the
  process correlates writes against the SSOT roster. Writes to
  authoritative columns originating from demoted instances fire the
  finding.
- **Consumer-direction analysis.** Connection-string inventory
  cross-referenced with the SSOT roster. Consumers reading from
  caches when SSOT is operationally reachable fire the finding.
- **OrgPath drift on the SSOT instance.** A change to
  `extensionAttribute1` on the SSOT instance's service account
  without a corresponding roster update fires the finding.

Remediation paths:
- Re-ratify (if the demoted instance has organically become the new
  authority — sometimes the operational reality has shifted and
  canon needs to catch up).
- Re-direct (if the demoted instance is incorrectly authoritative —
  redirect writes to canonical SSOT).
- Retire (if the contention exists only because retirement is
  overdue — execute the retirement plan).

`DRIFT-SSOT-CONTENTION` is distinct from `DRIFT-PROVENANCE` (which is
about substrate-canon vs. vendor-state divergence at the configuration
layer) and from the strategy paper's proposed `DRIFT-PERSISTENCE::stacked-sor`
(which is about vendor surfaces claiming SoR status for substrate-owned
facts). All three coexist; each has a different scope.

### 4.5 Operator workflow for ratification

The SSOT roster does not auto-populate from Phase 3 scoring. The
score is the *recommendation*; ratification is human governance.
Workflow:

1. **Auto-generated draft roster.** Phase 3 emits a draft roster in
   the same YAML shape as the canonical roster, but in a draft
   location (`inbox/mssql-rationalization/proposed-ssot-roster.yaml`).
2. **Steward review.** The governance steward reviews scores and
   recommendations per domain. Common adjustments: override the
   nominee based on procurement signals not visible in scoring
   (e.g., "PROD-DB-01 is being retired in 2027; nominate
   PROD-DB-02 instead even though it scores lower today").
3. **PR ratification.** Steward copies the (reviewed, adjusted)
   roster to the canon location and opens a canon-change PR with
   explicit rationale per overridden nomination.
4. **Governance-board review.** Board reviews the PR; ratification
   evidence (board minutes, dissents) is linked.
5. **Merge → enforcement begins.** The drift engine starts firing
   `DRIFT-SSOT-CONTENTION` against the live estate immediately on
   merge. Migration plans (Phase 5) execute against the ratified
   roster.

The four-step gating (draft → review → PR → board) prevents
auto-merge of high-blast-radius designations. The same gating shape
as canon governance for ADRs.

## 5. Phase 4 — Efficient-Target Selection (product-neutral)

For each cluster identified in Phase 2 and demoted-instance set
declared in Phase 3, select the target consolidation product.
**The process is product-neutral by doctrine** — it scores
candidates against a contract; the tenant picks. Canon names the
contract, not the product.

### 5.1 The operating-store contract (the scoring rubric)

Inherited from the companion strategy paper's amended §4.3 (after
the contract-first refactor recommended by the governance call).
A candidate product is *eligible* for selection only if it
satisfies every row:

| Contract requirement | Why it matters | Disqualifying violation |
|---|---|---|
| Relational, ACID transactional | Cross-canon referential integrity | Document or key-value stores |
| Entra-anchored auth (native or federated) | ADR-068 sequence | SQL Auth-only, Kerberos-only without federation path |
| FedRAMP Moderate or higher (in the deployment boundary) | UIAO_001 + GCC-Moderate scope | Self-hosted, no FedRAMP authorization, commercial-only-without-equivalent |
| TDE-equivalent at-rest encryption | SC-28 control mapping | Plain-disk storage |
| Column-level encryption capability | KSI-bearing rows, OrgPath history | No column-level encryption |
| Geographic / paired-region replication | FedRAMP continuity | Single-region only without DR plan |
| Change-data-capture stream | Data-lake projection (UIAO_109 v2.0 path) | No CDC; no audit log of changes |
| Standard SQL syntax | CQL transpiler portability | Custom DSL only |
| Read-only analytical mirror capability | Fabric/OneLake / Lakehouse pattern | No analytic-surface separation |

Candidates known to satisfy every row (under the right configuration):
- Oracle Database (OCI Autonomous Database, OCI Exadata, OCI VM-based DB)
- Microsoft SQL Server (Azure SQL Database, Managed Instance, Arc-enrolled SQL on Azure VM)
- Microsoft Fabric SQL endpoint (for read-mostly analytic workloads only — write OLTP needs a sibling primary)
- PostgreSQL (Azure Database for PostgreSQL Flexible Server, AWS RDS PostgreSQL on GovCloud)

Candidates that do *not* satisfy the contract (excluded):
- Microsoft Dataverse (not relational in the substrate sense)
- Azure Cosmos DB (document model)
- SQLite (single-writer; not network-addressable)
- Microsoft Access (not server-grade)

### 5.2 The efficiency scoring matrix

Among eligible candidates, scoring is per-cluster (not per-domain),
because the right target depends on the cluster's specific shape
(transactional vs. analytic, scale, regulatory tier).

| Dimension | Weight | Notes |
|---|---|---|
| **Existing-ELA reuse** | 0.20 | If the agency already has an ELA covering the candidate, factor in zero-marginal-cost; else add per-tenant licensing model |
| **Operational expertise alignment** | 0.15 | Agency DBA skillset; existing tooling investments; on-call coverage |
| **Workload-shape fit** | 0.15 | OLTP vs. analytic; high-write vs. read-heavy; row count scaling; partition-pattern fit |
| **Identity-integration efficiency** | 0.15 | Native Entra integration > federated; reduces round-trip latency per connection |
| **Compression / storage efficiency** | 0.10 | Bigger payoff at larger scale; Oracle Advanced Compression / Exadata HCC win at federal scale; Azure SQL DB page/row at small scale |
| **DR / continuity model alignment** | 0.10 | Geo-replication topology; existing DR site readiness |
| **Migration cost from current source** | 0.10 | Tools available (SSMA, Oracle Data Pump, native PostgreSQL replication, Fabric mirroring); cutover-window cost |
| **Lock-in risk** | 0.05 | Vendor-extension dependencies; portability of schema and stored procedures |

Per-cluster output is a ranked candidate list with scored breakdowns;
the tenant ratifies the selection. The substrate does not pick.

### 5.3 Worked example — a Finance consolidation cluster

To make the abstract scoring concrete, an illustrative cluster:

**Cluster `fin-gl-001`** — three regional Finance instances all
hosting variations of the General Ledger:
- `FIN-EAST-01\GL` — 47 GB, ~12M rows, SQL Server 2017, Windows Auth
- `FIN-WEST-01\GENLEDGER` — 62 GB, ~18M rows, SQL Server 2019, Windows Auth
- `FIN-CENTRAL-01\GL_NEW` — 8 GB, ~2M rows, SQL Server 2022 Azure-Arc-enrolled, mixed auth

Phase 3 designates `FIN-WEST-01\GENLEDGER` as SSOT (highest score
on population + capacity + boundary). Phase 4 scores three candidate
targets for the consolidation:

| Candidate | ELA reuse | Op expertise | Workload fit | Identity | Compression | DR | Migration cost | Lock-in | **Total** |
|---|---|---|---|---|---|---|---|---|---|
| Azure SQL DB (Single DB tier) | 0.9 (Azure ELA in place) | 0.8 | 0.75 (OLTP) | 1.0 (native Entra) | 0.5 | 0.85 | 0.7 (SSMA available) | 0.7 | **0.79** |
| Oracle Autonomous Database (OCI) | 0.3 (no existing OCI presence) | 0.5 (DBA team is Microsoft-centric) | 0.85 | 0.6 (federated only) | 0.95 (HCC) | 0.90 | 0.4 (cross-vendor migration) | 0.4 | **0.59** |
| PostgreSQL on Azure DB for PG | 0.7 | 0.65 | 0.7 | 0.7 | 0.55 | 0.85 | 0.5 (schema/proc rewriting) | 0.9 (open source) | **0.66** |

Recommendation: Azure SQL DB. Rationale: existing Azure ELA, DBA
expertise match, native Entra integration, lowest migration cost
from a SQL Server source.

But — a different agency with an existing Oracle ELA and DBA team
would score this very differently. The doctrine: present the
scored matrix; the tenant decides.

### 5.4 The hybrid case — Fabric SQL mirror without primary migration

A common federal pattern: consolidation is desirable but immediate
primary-platform migration is not. The substrate supports a "mirror
first, migrate later" pattern using Fabric SQL:

1. Designate SSOT per Phase 3.
2. Mirror the SSOT instance into a Fabric SQL endpoint (per OrgPath
   narrative chapter 07a).
3. Redirect read traffic from the demoted instances to the Fabric
   mirror over a transition window.
4. Reduce the demoted instances to write-only (legacy app writes
   continue; read traffic moves to Fabric).
5. Cut over remaining writes when the application's modernization
   schedule allows; retire the demoted instance.

This pattern uses Phase 4's scoring only to pick the *eventual*
target; the immediate consolidation work happens at the Fabric
mirror layer. Fabric SQL is read-optimized — it cannot be the
primary OLTP target for write-heavy workloads — but it can be the
*staging surface* that enables consolidation without forcing a
disruptive platform migration on day one.

### 5.5 Output of Phase 4

Per cluster:
- Eligible candidate list (passed the contract)
- Scored matrix (with explicit weight + signal breakdowns)
- Tenant-ratified target selection (recorded with rationale)
- Recommended migration tooling (SSMA, native replication,
  Fabric mirror, Oracle Data Pump, pg_dump+restore, etc.)
- Cutover-window estimate
- Risk-and-mitigation notes per candidate

These feed directly into Phase 5 (the merge playbook), which
sequences the work.

