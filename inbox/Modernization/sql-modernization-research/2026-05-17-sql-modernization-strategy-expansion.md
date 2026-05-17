---
title: "SQL Modernization Strategy Expansion — Single, Not Stacked Core Databases"
doc-type: research-draft
status: DRAFT
audience: ["governance-steward", "identity-engineer", "data-engineer", "network-engineering-steward"]
classification: Controlled
boundary: GCC-Moderate
owner: "Michael Stratton"
created_at: "2026-05-17"
canon-source: "inbox/Modernization/sql-modernization-research/ (research artifact — not canon)"
anchors:
  - "src/uiao/canon/UIAO-SSOT.md"
  - "src/uiao/canon/UIAO_007_OrgTree_Modernization_AD_to_EntraID_v1.0.md"
  - "src/uiao/canon/UIAO_010_OrgPath_in_Azure_Policy.md"
  - "src/uiao/canon/UIAO_011_OrgPath_in_Intune_and_Device_Governance.md"
  - "src/uiao/canon/UIAO_012_OrgPath_in_NAC_and_8021X.md"
  - "src/uiao/canon/UIAO_135_identity-directory-transformation-inventory.md"
  - "src/uiao/canon/specs/data-lake.md"
  - "src/uiao/canon/adr/adr-063-orgpath-storage-slot-binding.md"
  - "src/uiao/canon/adr/adr-068-kerberos-ntlm-elimination.md"
  - "src/uiao/canon/adr/adr-073-policy-targeting-nac-third-transport.md"
  - "src/uiao/modernization/directory-migration/adapters/sql-server/sql-server-adapter-interface.md"
  - "docs/customer-documents/orgpath-narrative/07a-uiao-beneath-the-azure-ssot-stack.qmd"
proposed-canon-actions:
  - "ADR-074 — Single Core Operating Database Doctrine"
  - "UIAO_013 — OrgPath in the Core Operating Database"
  - "UIAO_109 v2.0 — Data Lake anchored to a Core Operating Store"
  - "ADR-068 §amend — Auth modernization scope beyond SQL Server"
  - "DM_090 §amend — Workload → Substrate bridge"
  - "DRIFT-PERSISTENCE::stacked-sor — new drift sub-class"
---

# SQL Modernization Strategy Expansion — Single, Not Stacked Core Databases

> **Status.** Draft research artifact under `inbox/` (not canon). Promotion
> path is: (1) governance-steward review of the architectural argument in
> §4 and §9, (2) canon-change PR adding ADR-074 + UIAO_013, (3) amendments
> to UIAO_109, UIAO_135, ADR-068, and DM_090 as cited in §9.
>
> **Scope.** This document audits every SQL surface already present in
> the UIAO substrate, then proposes the architectural expansion the
> identity-modernization-program needs to converge on a single
> deterministic core operating database — not a stack of vendor SoRs —
> as the steady-state target after the AD-to-Entra modernization
> completes. The product opinion is explicit: **prefer single, not
> stacked, core databases**. The substrate's existing SSOT posture
> (UIAO_001) and OrgPath join-key model (UIAO_007 / UIAO_010-012)
> already support that opinion. This document makes the opinion
> canonical.
>
> **Out of scope.** Vendor-database internals (BlueCat NIOS schema,
> Cisco ISE policy-set encoding, ServiceNow CMDB class model) are
> referenced for boundary purposes only. The document does not specify
> SQL DDL; it specifies which databases the substrate considers
> authoritative, which it considers caches, and which it considers
> evidence sinks.

## 0. Executive Summary

UIAO already has a non-trivial SQL surface across five planes — identity,
network, workload, governance, and analytics. The surface was assembled
incrementally as adapters landed, and it has never been audited as one
thing. The audit in §1 produces four findings:

1. **SQL is everywhere, but no surface is canonical.** The substrate's
   own evidence and claim stores are file-system-backed (Evidence
   Bundle, IR pipeline, OSCAL exports); the Compliance Data Lake
   (UIAO_109) describes zones but names no operating database. Every
   vendor in the adapter graph brings its own SoR database (BlueCat
   NIOS, Infoblox NIOS / BloxOne, Cisco ISE, Aruba ClearPass,
   ServiceNow CMDB, SailPoint IIQ, Defender, Sentinel, Purview catalog,
   each Microsoft Graph endpoint). The substrate treats them all as
   equally authoritative, which is to say, none of them is.

2. **OrgPath is the existing join key — but it has nowhere central to
   land.** ADR-063 ratifies `extensionAttribute1` as the *Entra-side*
   storage slot, and ARM tag `OrgPath` as the *Azure-resource-side*
   slot. ADR-073 makes the NAC plane the third transport. Three
   transports, three writeback paths — and yet there is no canonical
   per-principal / per-resource / per-session row anywhere that the
   substrate owns end-to-end. The OrgPath value lives in Entra, in
   ARM, in NAC vendor policy stores, in Purview metadata, and in
   in-memory bundle objects. It does not live in a database the
   substrate controls.

3. **The "stacked databases" pattern is the default — and it is the
   federal SSOT failure mode.** Every vendor in the directory-migration
   inventory holds its own SoR DB and asks the substrate to integrate
   into it. That is exactly the pattern federal data-governance
   guidance (Evidence Act, Federal Data Strategy, CDO mandates) calls
   out as the root cause of SSOT collapse. The substrate's existing
   posture (UIAO_001) names this failure mode but does not yet specify
   the operating store that resolves it.

4. **Session-to-Tagged-Network-Security is the moment the gap becomes
   most visible.** When a device 802.1X-authenticates and the AAA
   server returns a VLAN, dACL, and SGT, that triple is a *session-
   tagged-network-security claim* — and there is no canonical place
   for it to land. Cisco ISE writes it to its own session table.
   Aruba ClearPass writes it to a different session table. Entra
   RADIUS Proxy writes it nowhere durable. Defender for Endpoint sees
   a partial view. Sentinel sees the RADIUS accounting log. Nothing
   joins them. ADR-073 introduces the contract for the *targeting*;
   it does not yet specify where the resulting *session evidence*
   lands canonically.

The proposed expansion (§4 + §9):

- **One core operating database** — a single Azure SQL database (with
  a Fabric SQL mirror for analytics) holds canonical rows for every
  principal (user, device, service principal, workload identity),
  every OrgPath node, every dynamic-group / AU / Conditional Access
  binding, every NAC session, every policy assignment, and every
  evidence event. Vendor SoRs become caches and edge stores; UIAO is
  the canonical writer.
- **OrgPath is the join key on every row.** The same string that
  travels in `extensionAttribute1`, in the ARM tag, in the device
  cert SAN OtherName, and in the NAC enforcement payload also lives
  as a foreign key in the core DB on every governed object.
- **Auth to the core DB is Entra-only.** ADR-068's SQL Server path
  generalizes: every connection to the operating DB uses managed
  identity, workload identity federation, or Entra CBA. No Kerberos,
  no NTLM, no SQL Auth, no shared service-account credentials.
- **Stacked vendor DBs are demoted to caches with a documented
  reconciliation contract.** A new drift sub-class —
  `DRIFT-PERSISTENCE::stacked-sor` — fires whenever a vendor surface
  is treated as authoritative for a fact the core DB already holds.

The case for "single, not stacked" rests on three observations
operators already know:

- Every stacked SoR is a drift surface — eventually it disagrees with
  the others, and reconciliation cost grows with the number of edges
  in the stack.
- Audit evidence built across stacked SoRs is forensic, not
  continuous — the evidence chain ends at each store's boundary.
- The OrgPath model only delivers deterministic governance if the
  join key resolves to the same row everywhere — which presumes
  there *is* a row, in a database the substrate writes.

The expansion proposed here is incremental and additive: no existing
canon is retired, three doctrinal documents are amended in place, and
two new canonical artifacts (ADR-074, UIAO_013) close the gap.

## 1. The SQL Surface Already in UIAO

This section is the audit. Every SQL-shaped surface the substrate
touches today is enumerated below, classified by plane, and tagged
with whether the substrate treats it as authoritative, as a cache,
or as evidence.

### 1.1 Identity-plane SQL — AD-anchored databases

The AD-to-Entra modernization inventory (UIAO_135 §1.2 row 7) names
**SQL Server Authentication — Service Identity** as a first-class
transformation: from Windows Auth (Kerberos / NTLM) plus SQL Auth (`sa`
accounts) to Entra ID auth for SQL 2022+ — MFA, Managed Identity,
Service Principal, OAuth 2.0 tokens via Arc. This is the only
transformation row in UIAO_135 that names a *database technology*
explicitly; every other row names an identity-plane construct (users,
SPNs, OUs, GPOs, devices) and leaves the data-plane sibling implicit.

The supporting artifacts already in canon:

| Artifact | Role |
|---|---|
| [`Spec3-D1.8-Get-SQLServerAuthAudit.ps1`](../../../src/uiao/canon/specs/) (referenced by UIAO_135 §3.2 and ADR-068) | Discovery script — enumerates SQL Server authentication mode, listening protocols, SPN registration, and Always-On AG identity per instance. Output is the authoritative input to the `DM_090` workload adapter. |
| [`DM_090 — SQL Server Workload Adapter Interface`](../../../src/uiao/modernization/directory-migration/adapters/sql-server/sql-server-adapter-interface.md) | Priority HIGH adapter that orchestrates SPN re-registration, service-account migration, Kerberos delegation preservation, certificate-based auth coordination, and the data-plane bridge into the Azure SSOT stack (OneLake mirror + Purview registration). |
| [`ADR-068 — Kerberos / NTLM Elimination`](../../../src/uiao/canon/adr/adr-068-kerberos-ntlm-elimination.md) | Sets the 2027-04-01 NTLM deprecation deadline, mandates Cloud Kerberos trust as the hybrid posture, and locks Entra CBA as the canonical modern-auth replacement. The ADR is explicit that the SQL Server path is *one workload class*; the broader auth modernization is intentionally left ADR-074-scoped. |
| [`Spec3-D1.1 — Get-ServiceAccountScan`](../../../src/uiao/canon/specs/Spec3-D1.1-Get-ServiceAccountScan.md) | Service-account scan that feeds every SPN-bearing workload, SQL Server included. Tied into `extract_spn_inventory()` in `src/uiao/adapters/modernization/active_directory/survey.py`. |
| `src/uiao/canon/computer-object-crosswalk.yaml` | Cross-walk for migrated computer objects; SQL Server hosts populate as a workload class. |

What this canon already says: SQL Server as a *workload* is
governed. The service account, the SPN, the delegation chain, the
certificate-based authentication path, the post-migration drift
surface (§7.1 of `docs/docs/16_DriftDetectionStandard.qmd`) — all are
named, with adapter-anchored contracts.

What this canon does *not* yet say: which database the *substrate
itself* runs on. The DM_090 adapter migrates other people's SQL
instances. It does not declare a SQL instance UIAO operates as its
own canonical store.

### 1.2 Network-plane SQL — vendor-private datastores

The network-plane adapters all carry vendor-private databases that
behave as SoRs for the surface they govern. The current inventory:

| Vendor surface | Backing store | UIAO treatment today | Authoritative for? |
|---|---|---|---|
| BlueCat Address Manager (DM_010) | PostgreSQL-backed BAM database (vendor-managed) | Read-through adapter — `src/uiao/adapters/bluecat_adapter.py`; canon consumes IPAM facts but does not write back | IP allocations, VLAN definitions, DNS records (legacy) |
| Infoblox NIOS Grid / BloxOne DDI | Embedded NIOS DB / BloxOne CSP cloud store | Read-through adapter — `src/uiao/adapters/infoblox_adapter.py` | Same — IP, VLAN, DNS, DHCP |
| Cisco ISE | Internal Oracle / Postgres policy store + session table | No first-party adapter today; ADR-047 / ADR-073 plan ERS API + pxGrid integration | RADIUS sessions, policy sets, posture, SGT registry |
| Aruba ClearPass | Internal PostgreSQL policy store + session table | Same — registered category, no live adapter | RADIUS sessions, services, posture profiles |
| Entra RADIUS Proxy (NPS Extension for Entra Auth) | Microsoft-managed (no exposed DB) | Graph-only — consumes Entra group memberships | RADIUS sessions on the Microsoft side; ephemeral |
| NPS (legacy hybrid window) | Local SAM + AD-bound | Tagged as hybrid-window-only by ADR-073 §D4; pairing rule prevents drift | RADIUS sessions, connection request policies |
| Palo Alto NGFW (UIAO_142 / WS-A5) | PAN-OS embedded config + log forwarder | Adapter present (`paloalto_adapter.py`); reads policy and feeds drift | Policy rules, session log forwarding |
| AD CS / Cloud PKI | AD-integrated cert template store / Microsoft Cloud PKI | PKI adapter (`pkica_adapter.py`); ADR-068 sets target state | Issued cert inventory, template definitions |

Every one of these vendor surfaces is, at minimum, a session-evidence
producer; most of them claim SoR status for the facts they govern.
The substrate today treats them as truthful and reads through —
which is correct for the facts the vendor authors (e.g., Infoblox
*is* the IPAM SoR) but incorrect for facts UIAO authors (e.g.,
the OrgPath-to-VLAN binding ADR-073 declares).

That dual treatment — vendor-as-SoR for some facts, substrate-as-SoR
for others — is the surface area for the stacked-databases problem
that §2 develops.

### 1.3 Workload-plane SQL — the on-prem and Azure SQL estate

The workload-plane SQL inventory is what the DM_090 adapter governs:
on-prem SQL Server (2016+), Azure Arc-enrolled SQL Server, Azure SQL
Managed Instance, Azure SQL Database (single + elastic pool), and
Microsoft Fabric SQL endpoint (post-mirror). The
[OrgPath narrative chapter 07a](../../../docs/customer-documents/orgpath-narrative/07a-uiao-beneath-the-azure-ssot-stack.qmd)
develops the strategic frame for this layer: UIAO sits *beneath* the
Microsoft Fabric / OneLake / Purview stack as the identity governance
substrate that makes the Azure data SSOT trustworthy.

The relevant facts:

- Every on-prem SQL Server instance maps to an OrgPath segment via
  its service-account principal (preferred) or hosting computer
  (fallback). Unattributed instances emit a `DRIFT-IDENTITY` P2
  finding before migration can proceed.
- OneLake mirroring lets the operational SQL estate stay running
  while the data appears in Fabric workspaces governed by Fabric
  Domain assignments that mirror the OrgPath hierarchy. The
  workspace-to-domain assignment is a *separate* mechanism from the
  user-plane Adaptive Policy Scopes — chapter 07a calls this the
  user-plane / data-plane asymmetry.
- Purview data-map collections inherit OrgPath as a custom metadata
  field on every SQL asset discovered by Purview scans. The field
  name is `uiao_orgpath`.

What the workload plane has that the network plane does not: an
explicit declared target architecture (the Fabric / OneLake / Purview
stack) and an explicit declared identity model (Entra-anchored).
What the workload plane does *not* yet have: a canonical answer to
"which of the migrated SQL instances is the substrate's *own*
operating store?" Today the answer is "none of them" — the
substrate's stores are file-system bundles and JSON evidence
artifacts.

### 1.4 Governance-plane SQL — substrate bundles, claims, and evidence

The substrate's own data layer is described in
[`src/uiao/canon/specs/data-lake.md`](../../../src/uiao/canon/specs/data-lake.md)
(UIAO_109 — Compliance Data Lake Model). Three zones — Raw,
Normalized, Curated — partitioned by tenant / date / evidence
source, with immutable append-only writes and SHA-256 anchoring.

What UIAO_109 declares: a zone model.

What UIAO_109 does *not* declare: an operating database. The CQL
engine (UIAO_108) is described as "SQL-like queries over bundles" —
the bundles being filesystem artifacts. The Evidence Graph (UIAO_113)
traces provenance across bundles. The IR pipeline produces JSON, not
rows. The KSI library evaluates against canonical YAML data
(`canon/data/orgpath/*.yaml`). The substrate has the *shape* of a
database — entities, claims, provenance, drift — and the *language*
of a database (CQL), but it does not commit to a database product as
the canonical store.

The
[`database_base.py`](../../../src/uiao/adapters/database_base.py)
abstract base class is the closest the codebase comes to declaring a
canonical persistence contract. It defines:

- `ConnectionProvenance` — identity, auth method, endpoint, TLS, mTLS
- `SchemaMappingObject` — vendor schema → UIAO canonical schema
- `QueryProvenance` — canonical query, vendor query, plan hash, row count
- `ClaimObject` and `ClaimSet` — minimal authoritative claims
- `DatabaseAdapterBase` — abstract verbs (connect, read, normalize, claim)

It is a *vendor-database-adapter* contract, intended for adapters
that read from vendor SQL or document stores and emit canonical
claims. It is *not* a contract for the substrate's own operating
store, and it does not name a target.

### 1.5 Analytics-plane SQL — Fabric, OneLake, Purview catalog

The analytics-plane is where the substrate already concedes ground to
the Microsoft Fabric / OneLake / Purview stack. Chapter 07a's
position:

> "OneLake provides a single logical data lake per tenant, with
> zero-copy shortcuts and near-real-time mirroring that eliminate
> duplicate SQL Server instances without rip-and-replace. Microsoft
> Purview provides the governance and metadata control plane: catalog,
> lineage, sensitivity labels, data products, and authoritative-record
> designations. Fabric SQL and Azure SQL provide the operational and
> transactional layer."

This is correct, and the substrate consumes from this stack via
Purview adapters, Fabric Domain reconciliation, OneLake shortcut
authorization (via Entra managed identity), and Defender for Cloud
Apps (for SaaS-shaped data flow surfaces). The analytics-plane
treatment is mature.

What this plane does *not* yet do: serve as the substrate's
*operating* store. Fabric SQL endpoints are read-optimized; OneLake
is append-mostly; Purview is metadata-only. None of them is the
right place for the substrate's own transactional state — for
example, the row that says "the Conditional Access policy
`CA-FIN-RequireCompliant` is targeted at dynamic group
`OrgTree-FIN-Users` as of 2026-05-15T14:32:01Z, written by managed
identity `mi-uiao-orchestrator`, derived from canon SHA-256
`a3f1...`."

That row needs an operational database. §4 names it.

## 2. The "Stacked Databases" Problem

### 2.1 What "stacked core databases" means in a federal identity estate

"Stacked core databases" is the steady-state pattern that emerges when
every vendor in the modernization graph holds its own system-of-record
database and asks the substrate to integrate into it. The substrate
ends up *consulting* each store rather than *owning* the canonical
fact. Each store has its own schema, its own access model, its own
backup and HA story, its own audit log, and its own drift surface.

The stacking is rarely deliberate. It accumulates because:

- Each procurement decision (CMDB, IPAM, IGA, NAC, EDR, SIEM, IdP,
  HR, PKI) is made by a different sub-organization on a different
  cadence. Each vendor brings a database because that is the only
  way the vendor has ever shipped its product.
- "Integration" is normalized as a directional concept — vendor A
  exposes an API, vendor B consumes it, the substrate sits in the
  middle. Nobody asks whether a canonical row exists anywhere or
  whether the integration just propagates copies.
- Federal data-governance guidance (Evidence Act, Federal Data
  Strategy, CDO mandates) instructs agencies to designate
  authoritative sources — but the guidance speaks to *data domains*,
  not to *identity governance state*. Identity governance has
  historically been excluded from the SSOT conversation, which is
  why the
  [`federal-ssot-alignment.qmd`](../../../docs/customer-documents/whitepapers/federal-ssot-alignment.qmd)
  whitepaper exists.

### 2.2 Inventory: every database that currently demands SSOT status

This is the inventory of databases the substrate touches whose
vendors expect to be authoritative for at least one fact UIAO also
wants to be authoritative for. Each row is a stacked-SoR candidate.

| Database | Vendor authority claim | UIAO canon view | Conflict? |
|---|---|---|---|
| Active Directory NTDS.dit | Authoritative for *all* directory state in the legacy world | Source of truth *during* migration only; superseded by Entra at cutover (ADR-001, ADR-002, ADR-042, ADR-068) | Resolved by migration; AD retires |
| Entra ID (Microsoft-managed) | Authoritative for identity, devices, app registrations, groups | Substrate *consumes* Entra as the identity-plane source; OrgPath lives in `extensionAttribute1` (ADR-063) | Partial — Entra owns identity facts, UIAO owns OrgPath as a substrate-authored attribute *stored in Entra* |
| Azure Resource Manager (ARM) tags | Authoritative for Azure resource state | Same — UIAO writes the `OrgPath` ARM tag; ARM stores it | Same partial — ARM owns the resource, UIAO owns the tag |
| BlueCat / Infoblox IPAM DB | Authoritative for IP, VLAN, DNS, DHCP allocations | UIAO consumes IPAM facts via adapter; cross-canon integrity check in ADR-073 requires VLAN IDs to resolve in IPAM canon | UIAO does *not* claim authority over IP / VLAN allocation — clean SoR boundary |
| Cisco ISE / Aruba ClearPass policy DB | Authoritative for RADIUS policy sets, posture profiles, session state | UIAO authors the *targeting binding* (ADR-073 `nac_assignments[]`); the AAA server authors the *policy body* | **Conflict** — targeting and session-evidence rows have no canonical UIAO home |
| ServiceNow CMDB | Authoritative for configuration items, IT service management | UIAO consumes CMDB facts (`servicenow_adapter.py`) | **Conflict** — CMDB wants to be SoR for OrgPath assignment on assets; UIAO canon says Entra `extensionAttribute1` is the slot |
| SailPoint IdentityIQ / NER | Authoritative for identity governance workflows, non-employee risk | UIAO Single-ATO reciprocity model (ADR-054, UIAO_140) treats SailPoint as a reciprocity input | **Conflict** — IGA workflows want to own access lifecycle, but Entra ID Governance also does, and UIAO needs OrgPath written by exactly one writer |
| CyberArk PAM vault | Authoritative for privileged credential state | UIAO consumes via `cyberark_adapter.py` and `cyberark_sync_orchestrator.py` | Clean — vault is SoR for credentials only |
| Defender for Endpoint / Cloud / Servers | Authoritative for device exposure, vulnerability, EDR posture | UIAO consumes telemetry, OrgPath references resolved at query time | Clean — telemetry, not SoR for identity |
| Microsoft Sentinel | Authoritative for security event log aggregation | UIAO consumes via SIEM adapter; KQL queries reference OrgPath | Clean — log store, evidence sink |
| Microsoft Purview catalog | Authoritative for data asset metadata, lineage, sensitivity | UIAO writes `uiao_orgpath` custom metadata field on every asset | Clean — Purview is SoR for data assets, UIAO owns the OrgPath join key |
| HR system (Workday / Oracle, candidate per UIAO_135 §2.1) | Authoritative for employment state, manager chain, cost center | UIAO consumes HR via API-driven inbound provisioning (ADR-003, Spec2-D3.x); HR populates `manager`, `department`, `companyName`, and the source for OrgPath segments | Clean *if* the HR-to-Entra-to-UIAO pipeline is the only path; conflict if HR also writes a downstream CMDB independently |
| Each SQL Server instance the agency operates | Authoritative for its application's transactional state | DM_090 governs the migration | Clean — application state is not substrate state |
| **Substrate's own operating store** | — | **Undeclared today** | **This is the gap §4 closes** |

The row that matters: the last one. The substrate has no *named*
operating database. Its claims live in JSON bundles, its canon lives
in YAML / Markdown files, its evidence lives in the Evidence Bundle
directory structure, its provenance lives in SHA-256-anchored
content-addressed records. All of these are fine for *immutable
canon* (canon is read-only at runtime per UIAO_001), but they are
not fine for the operating state the substrate produces — the
adapter plan / apply / reconcile receipts, the NAC session evidence,
the policy-targeting authoritative bindings, the drift-finding
ledger. That operating state has no relational home.

### 2.3 Drift cost of stacking

The cost of leaving the stacked-databases pattern unaddressed is
measured in drift findings. The substrate already classifies five
drift classes (UIAO-SSOT §"Drift baseline"); each of them has a
stacked-SoR multiplier:

| Drift class | Stacked-SoR multiplier |
|---|---|
| `DRIFT-SCHEMA` | Every vendor SoR has its own schema; "schema drift" multiplies by the number of stores that hold a copy of the affected attribute |
| `DRIFT-SEMANTIC` | Vendor stores re-encode the same fact in different units / vocabularies; semantic reconciliation is a per-edge cost |
| `DRIFT-PROVENANCE` | Every cross-store reference is a potential dangling pointer; the substrate has to verify all of them on every walk |
| `DRIFT-AUTHZ` | Every store has its own RBAC; an authoritative role change in one does not propagate to the others without an explicit pipeline |
| `DRIFT-IDENTITY` | A user / device / service principal resolves differently in each store; reconciliation is the substrate's load-bearing function |

The complexity of stacked-SoR reconciliation grows with `O(N²)` in
the number of stores (each pair needs a contract). The complexity of
canonical-store reconciliation is `O(N)` — each vendor reconciles to
the one canonical store, not to every peer. The federal SSOT
guidance is correct; the question UIAO has to answer is what the
canonical store *is*.

### 2.4 The vendor-economics of stacked databases

Vendors prefer to be SoRs. Three economic forces make this so:

1. **Lock-in.** A vendor whose store is SoR for a domain is
   structurally harder to displace. Migration off a vendor SoR
   requires data extraction, schema mapping, and historical evidence
   re-anchoring — all of which favor the incumbent.
2. **Pricing surface.** Vendor pricing typically scales with the
   number of objects under management. A vendor that holds the SoR
   counts every governed object; a vendor that holds a cache counts
   only what passes through.
3. **Audit posture.** A vendor whose store is SoR can sell audit and
   compliance reports as standalone deliverables; a cache vendor
   cannot.

The substrate's response is not to refuse vendor SoR claims — vendors
*should* be SoR for the facts their products inherently produce
(BlueCat for IP allocations, ISE for RADIUS policy bodies, Purview
for data lineage). The substrate's response is to refuse stacking
*for the substrate's own facts*: OrgPath, dynamic-group / AU
bindings, policy targeting, session-tagged-network-security claims,
provenance, drift findings. Those rows live in one operating
database, which is the substrate's.

## 3. UIAO's Existing Posture (and where it stops short)

### 3.1 UIAO_001 SSOT — "every claim has exactly one canonical source"

The Operating Principle is unambiguous:

> "**SSOT** — every claim has exactly one canonical source under
> `src/uiao/canon/`. All other representations are
> provenance-anchored pointers."  
> *(AGENTS.md §"Operating principles", UIAO_001 §"Scope")*

The principle is correct and load-bearing. It defines *canon* — the
governance documents — as the SSOT. It does not define an *operating*
store, because canon is read-only at runtime (UIAO_001 §"Canon-
consumer rule" + Repository Invariant I4) and the substrate's
runtime state was not yet declared at the time UIAO_001 was authored.

The expansion in §4 extends the SSOT principle to the operating
layer: every operating claim (every plan op, every apply receipt,
every drift finding, every session-tagged-network-security record)
also has exactly one canonical source — the core operating database.
Canon governs *what the substrate is configured to do*; the core
operating database governs *what the substrate has actually done and
observed*.

### 3.2 The Compliance Data Lake (UIAO_109) — zones, but no anchor DB

UIAO_109 is currently a zone-and-partitioning model with no named
operating store. Three zones (Raw / Normalized / Curated),
three partition axes (tenant / date / evidence source), immutable
append-only writes, hash + provenance per object, CQL + Auditor API
access. The model is correct as far as it goes; what it does not say
is *where the rows live*.

A natural extension: the data lake is the **analytical** projection
of the operating store. The operating store is the transactional
write surface; the data lake is the columnar / OneLake / Fabric
mirror that supports the CQL engine, the Evidence Graph, and the
KSI library. §9.3 proposes UIAO_109 v2.0 to make this explicit.

### 3.3 DM_090 SQL Server adapter — workload-level only

DM_090 (the SQL Server adapter interface) governs *the agency's*
SQL Server instances during migration. It is not the substrate's
own store. The DM_090 contract:

- Inputs: SPN inventory, service-account scan, OrgPath attribution.
- Outputs: re-registered SPNs, migrated service accounts, validated
  Kerberos delegation, OneLake mirror + Purview registration.
- Drift: §7.1 of `docs/docs/16_DriftDetectionStandard.qmd` — four
  SPN drift conditions.

The adapter is correct for what it covers. It does not extend to:
*Which SQL instance is the substrate's own?* That question is
canon-level, not adapter-level, and §4 + §9.1 + §9.2 answer it.

### 3.4 Adapter `database_base.py` — vendor DB abstraction, no canonical store

The
[`src/uiao/adapters/database_base.py`](../../../src/uiao/adapters/database_base.py)
ABC declares the contract for *any* database adapter: read from
vendor, produce normalized claims, attach provenance. The ABC names
seven responsibility domains (connection provenance, schema mapping,
query provenance, claim objects, claim sets, the abstract base
itself, and an evidence-emission verb implied by the surrounding
codebase).

What the ABC does not do: name a canonical operating store the
substrate itself targets. Every adapter that implements the ABC
points outward (to a vendor system) rather than inward (to the
substrate's own DB).

The expansion in §4 introduces an inward-pointing adapter — the
*core operating database adapter* — that implements the same ABC
but targets the substrate's canonical Azure SQL instance.

### 3.5 The Gap: no canonical "core operating database" in canon

Summarizing §3.1 – §3.4: the substrate has

- canon as SSOT (UIAO_001), correctly defined and read-only
- a data-lake zone model (UIAO_109), correctly scoped to analytics
- a workload-migration adapter (DM_090), correctly scoped to other
  people's SQL instances
- a vendor-database ABC (`database_base.py`), correctly scoped to
  reading from vendor stores

and is missing one thing: a canonical declaration of the operating
database the substrate itself runs on, and the contract for how
adapter outputs, plan / apply receipts, drift findings, and session
evidence land there.

That gap is what §4 fills.

## 4. The "Single, Not Stacked" Modernization Argument

### 4.1 What a single core operating database delivers

A *single* core operating database is a single addressable relational
store, declared as canonical by ADR-074, that holds every operating
fact the substrate produces and every join key the substrate needs
to reconcile across vendor SoRs. "Single" is the property; it is
contrasted with *stacked*, where each vendor surface holds its own
SoR for the same class of fact.

What single delivers that stacked cannot:

- **One authoritative row per governed object.** A user has one row.
  A device has one row. An OrgPath has one row. A policy assignment
  has one row. A NAC session has one row. The substrate writes; the
  vendor stores cache, reflect, or evidence.
- **Referential integrity as a first-class governance property.**
  ADR-073 already requires the loader to check that every
  `target_group` resolves in `dynamic-groups.yaml` and every
  `vlan_id` resolves in IPAM canon. Today those checks are
  cross-file YAML reads. With a single operating store, they become
  database-enforced foreign keys — drift detected at write time, not
  at the next walk.
- **A canonical projection surface.** The data lake (UIAO_109) and
  the Evidence Graph (UIAO_113) become *projections* of the
  operating store — populated by change-data-capture from one
  authoritative writer, not by reconciling N vendor surfaces.
- **A queryable substrate.** CQL (UIAO_108) was specified as "SQL-
  like queries over bundles." With a single operating store, CQL
  resolves to actual SQL against the canonical relational schema —
  queries become deterministic, the execution plan is visible, and
  performance is tunable.
- **One audit boundary.** Audit evidence for the substrate's own
  state is sourced from one store with one TLS/mTLS auth model, one
  RBAC model, one immutable change-data-capture log. FedRAMP-grade
  evidence assembly stops needing to be retrospective.

What single does *not* attempt to be:

- **The vendor SoR for every fact.** BlueCat still owns IP
  allocations. ISE still owns RADIUS policy bodies. Purview still
  owns data-asset lineage. The core operating database does not
  duplicate these stores; it holds the *bindings* that connect them
  to OrgPath and to the substrate's enforcement contracts.
- **A monolith.** Single does not mean "one schema for everything."
  The core database has a normalized schema with bounded contexts —
  identity, OrgPath, policy, NAC sessions, evidence events. A
  Fabric SQL mirror provides the columnar analytics surface. The
  substrate stays modular; only the *write path* is single-anchored.

### 4.2 OrgPath as the row-level key that makes one DB work

The single-core argument is only viable because UIAO already has a
deterministic join key — OrgPath — and a ratified storage slot for
that key (ADR-063). The expansion is mechanical, not invented:

- Every row in the core operating database that represents a
  governed object (user, device, service principal, workload
  identity, computer, server, NAC session, policy assignment,
  evidence event) carries an `orgpath` column.
- That column references a canonical `orgtree_node` table whose
  rows are loaded from `canon/data/orgpath/codebook.yaml`
  (UIAO_151).
- The column is non-nullable for every object type that has an
  Active OrgPath; for objects in transit (newly enrolled devices
  pre-Intune-First Pillar 1) the column carries the quarantine
  value `ORG-BRANCH-UNPOSITIONED`.
- A deviation between the value in the core DB and the value in
  the vendor surface (Entra `extensionAttribute1`, ARM tag, NAC
  enforcement payload, Intune device cohort, cert SAN OtherName,
  Purview `uiao_orgpath` field) is exactly the
  `DRIFT-PROVENANCE` class — caught by the substrate walker.

The three transports declared by ADR-073 (Intune, Azure Policy,
NAC) become three *writeback paths* from the core DB. The
substrate's adapter dispatches the OrgPath value to all three; if
any one drifts, the walker fires.

### 4.3 Candidate target — Azure SQL DB, with a Fabric SQL mirror for analytics

The target selection is opinionated. The candidates and their
trade-offs:

| Candidate | For | Against | Verdict |
|---|---|---|---|
| **Azure SQL Database (single DB tier)** | GCC-Moderate authorized; Entra-only auth supported (Managed Identity + AAD principals); transparent data encryption + Always Encrypted column-level encryption; geo-replication; Azure Backup; PaaS — no patching surface | Microsoft-managed; tenant-bound; lock-in to Azure pricing | **Recommended target.** Boundary fit, auth fit, and PaaS posture align with ADR-068 §"Cloud Kerberos trust" doctrine and UIAO_001 §"Canon-consumer rule". |
| **Azure SQL Managed Instance** | Higher SQL Server feature parity (CLR, Service Broker, cross-DB queries, SQL Agent) | Costlier, slower provisioning, VNet-anchored | Reserve for the agency's migrated SQL workloads (DM_090). Not the substrate's store. |
| **Microsoft Fabric SQL endpoint (Lakehouse / Warehouse)** | OneLake native; read-optimized; columnar; integrated with Purview | Append-mostly; not transactional; high latency for OLTP writes | **Mirror target, not primary.** The core OLTP store mirrors *into* a Fabric Lakehouse for analytics + CQL execution. |
| **Microsoft Dataverse** | Identity-anchored (Entra-bound by default); model-driven; rich audit | Power-Platform-coupled; throughput limits at substrate scale | Reject. Not a relational substrate. |
| **Cosmos DB** | Multi-model; global distribution; strong consistency option | Document-model semantics complicate the relational join the core DB needs | Reject. Wrong shape. |
| **PostgreSQL on Arc (or Azure Database for PostgreSQL)** | Open source; portable; cross-cloud | GCC-Moderate auth path less mature than Azure SQL; another vendor relationship; less native Entra integration | Reject for the substrate. Reasonable for vendor-side adapters; not for UIAO's canonical store. |
| **SQLite (current de-facto in bundles)** | Already used implicitly for some IR pipeline artifacts | Single-writer; not network-addressable; no Entra auth | Reject. Suitable only for ephemeral per-bundle artifacts. |

The target stack:

- **Primary OLTP store:** Azure SQL Database, single database tier,
  GCC-Moderate aligned, Entra-only auth, Always Encrypted on
  sensitivity-tagged columns (KSI-bearing fields, OrgPath history,
  evidence payloads).
- **Analytical mirror:** Fabric SQL endpoint on a Lakehouse mirrored
  from the primary OLTP store via Fabric mirroring (per OrgPath
  narrative chapter 07a).
- **Backup + audit:** Azure Backup vault; immutable change-data-
  capture log streamed to Sentinel via the SIEM adapter for
  FedRAMP continuous-monitoring evidence.

### 4.4 The vendor SoR pattern — edge caches, canonical-by-reference, not authoritative

Vendor surfaces remain in the architecture, but with a documented
demotion: each vendor is *either* SoR for a fact the substrate does
not own, *or* a cache that reconciles to the core operating DB. No
vendor is silently authoritative for substrate-owned facts.

| Vendor surface | Status under the new doctrine | Reconciliation path |
|---|---|---|
| Entra ID directory | **SoR** for identity, devices, app registrations, group memberships | UIAO writes `extensionAttribute1` (OrgPath) and reads back; the core DB stores the *binding declaration*, Entra stores the *applied value*; drift = `DRIFT-PROVENANCE` |
| ARM (Azure resource tags) | **SoR** for Azure resource state | Same pattern — UIAO writes `OrgPath` ARM tag; core DB holds the canonical binding |
| BlueCat / Infoblox IPAM | **SoR** for IP / VLAN / DNS / DHCP allocations | UIAO consumes; the core DB holds the *VLAN-to-OrgPath binding* as a foreign-key joining vendor SoR rows to canon |
| Cisco ISE / Aruba ClearPass | **Cache** for OrgTree-targeted policy assignments; **SoR** for policy bodies and live session state | UIAO writes the assignment (`nac_assignments[]`) to the AAA server; the core DB stores the canonical assignment row; session evidence streams *into* the core DB (§7) |
| ServiceNow CMDB | **Cache** for OrgPath on CIs; **SoR** for IT service management process state | UIAO writes OrgPath into the CMDB record; the core DB is the authoritative writer |
| SailPoint NER | **SoR** for non-employee risk score and entitlement-review evidence | UIAO consumes risk findings per ADR-059; OrgPath is read-back from Entra, not from SailPoint |
| HR system (Workday / Oracle) | **SoR** for employment state, manager chain, cost center | UIAO consumes via API-driven inbound provisioning; HR is the *origin* writer of identity attributes, Entra is the *immediate* writer, core DB is the *canonical* writer for OrgPath |
| Defender suite | **Evidence** sink — telemetry, vulnerability, posture | Consumed via Defender adapters; core DB holds joins by OrgPath at query time |
| Sentinel | **Evidence** sink — security event log | Consumed via SIEM adapter; correlation queries reference OrgPath as the join key |
| Purview catalog | **SoR** for data-asset lineage and sensitivity classification | UIAO writes `uiao_orgpath` custom metadata; core DB holds the canonical OrgPath, Purview holds the data-asset reference |
| Microsoft Sentinel UEBA, Cloud App Security, Threat Intel | **Evidence** sinks | Same — telemetry only |
| AD CS / Cloud PKI | **SoR** for issued certificate inventory | UIAO writes the SAN OtherName OrgPath template token (ADR-073 §D5); core DB holds canonical OrgPath, cert authority holds the issued cert |

The pattern is uniform: *substrate-authored attributes live in the
core DB and reflect outward; vendor-authored facts live in the
vendor SoR and reflect inward as reference data*. The contract is
explicit, the drift surface is explicit, and the audit chain is one
hop, not N.

### 4.5 Where stacked persistence is permitted (and where it is not)

Two cases where stacking is operationally necessary and remains
permitted under the new doctrine:

1. **Hybrid migration windows.** During the AD-to-Entra cutover, the
   AD NTDS and Entra directories coexist. ADR-073 §D4 already
   permits NPS + cloud-RADIUS pairing during the DM_030 migration
   window, with a loader-enforced pairing rule. The same shape
   applies to any source-target migration: paired entries, loader-
   enforced twin rule, retirement-gate checklist.

2. **Vendor-internal session and event tables.** Cisco ISE's session
   table, ClearPass's session table, Defender's incident table,
   Sentinel's event store — these are *operational* tables internal
   to the vendor product. UIAO does not require them to be eliminated.
   What UIAO requires is that the *authoritative* session-tagged-
   network-security claim (the OrgPath ↔ VLAN ↔ device ↔ time tuple
   that the substrate evaluates) lands in the core DB; the vendor's
   own tables remain as the vendor's operational scratch.

What is *not* permitted under the new doctrine:

- A second SoR for OrgPath. There is one writer (UIAO orchestrator
  via the core DB) and one slot in Entra (`extensionAttribute1`) /
  one slot in ARM (`OrgPath` tag). Any other claim of SoR for
  OrgPath is a `DRIFT-PERSISTENCE::stacked-sor` finding.
- A second SoR for dynamic-group / AU / Conditional Access targeting
  bindings. UIAO_152 + UIAO_154 + ADR-073 + ADR-039 + ADR-036 +
  ADR-037 already specify the authoring surface; the core DB is the
  operating projection.
- A second SoR for NAC session evidence as the substrate evaluates
  it (§7). Each AAA vendor's session table remains operational; the
  substrate's session-tagged-network-security claim is one row in
  the core DB per session, sourced from the vendor accounting log.

## 5. AD → Entra ID Modernization Through a Single Core Database Lens

### 5.1 The auth surface — extending ADR-068 beyond SQL Server

ADR-068 sets three canonical positions: NTLM deprecation by
2027-04-01, Cloud Kerberos trust as the hybrid posture, Entra CBA as
the modern-auth replacement. Its scope statement is explicit that
the SQL Server path is *one workload class* — Spec3-D1.8 covers it.
The ADR leaves the *broader auth modernization* for DB-bearing
services other than SQL Server open.

The expansion ADR-074 should make explicit:

- **The core operating database is Entra-only.** Connections to the
  substrate's Azure SQL DB use managed identity (for service-to-
  service), workload identity federation (for federated agent
  identities), or Entra CBA (for privileged human access). No SQL
  Auth, no Kerberos, no NTLM. This applies from day one — there is
  no migration window, because the core DB is greenfield.
- **Every other DB-bearing surface UIAO consumes follows ADR-068's
  sequence.** Vendor SoRs (BlueCat, Infoblox, ServiceNow, SailPoint,
  ISE, ClearPass) authenticate per the vendor's modernization plan
  — most are already cloud-native or have an Entra federation path.
  Adapters declare their auth method in `ConnectionProvenance`
  (`database_base.py`) so the substrate's own audit log captures
  the choice.
- **The vendor-side SQL Server estate follows DM_090.** SPN re-
  registration, service-account migration, Cloud Kerberos trust for
  hybrid clients, Entra Managed Identity for cloud-anchored
  applications. Same doctrine ADR-068 already sets.

ADR-068's exception-class mechanism carries forward: legacy
applications that cannot meet 2027-04-01 file per-app ADRs with the
inability-to-migrate reason and the compensating control. The new
doctrine does not change that mechanism; it expands the scope of
what the deadline applies to.

### 5.2 OrgPath as the row-level join — extending ADR-063 to the core DB

ADR-063 ratifies `extensionAttribute1` as the per-principal storage
slot in Entra. ADR-063 §5 *defers* a `DRIFT-SCHEMA::slot-occupied`
sub-class. ADR-074 should retroactively close that deferral by
adding the corresponding `DRIFT-PERSISTENCE::stacked-sor` sub-class
that fires when:

- a vendor surface other than Entra is writing OrgPath, or
- a vendor surface is reading OrgPath from somewhere other than
  the canonical slot (Entra `extensionAttribute1` for principals,
  ARM tag `OrgPath` for resources, core DB OLTP row for substrate-
  owned operating state).

The core DB carries an `orgpath` column on every governed-object
table. The column is populated by:

1. The OrgTree pipeline (canonical writer).
2. Re-read from Entra `extensionAttribute1` for principals on every
   walk (drift detection — the core DB row is the canonical value,
   Entra reflects).
3. Re-read from ARM tag `OrgPath` for Azure resources.
4. Re-read from device cert SAN OtherName for the NAC plane.

Disagreement between these reads and the canonical column is
`DRIFT-PROVENANCE` (one of the four read-back targets is stale).
Disagreement between the canonical column and *another database*
claiming SoR status is `DRIFT-PERSISTENCE::stacked-sor`.

### 5.3 Service identities and managed identities as the auth path

The AD-to-Entra modernization for *service identities* — the
accounts SQL Server, IIS, scheduled tasks, and middleware historically
authenticate as — converges on a small target set:

| Source | Target | Carrier of OrgPath |
|---|---|---|
| AD service account (`svc-*` user) | Managed Identity (Azure-hosted) or Workload Identity Federation (multi-cloud / federated agent) | Service Principal `extensionAttribute1` |
| gMSA | Managed Identity (with delegated permission via Entra App Registration) | App Registration's app `tags` |
| Local SYSTEM-account workload | Workload identity federation (per ADR-004) | Federated identity's claim |
| SQL Server instance service account (`MSSQLSvc/*`) | Managed Identity (Azure SQL MI) or Arc-onboarded managed identity (on-prem SQL Server) | SPN's principal `extensionAttribute1` |

Every one of these target identities reads from / writes to the core
operating DB using Entra auth; the core DB grants schema-scoped
permissions to a small set of Entra security groups (`db-uiao-writer`,
`db-uiao-reader`, `db-uiao-admin`) that are themselves OrgPath-scoped
(targeted via dynamic group rules on OrgPath segments via the
existing ADR-039 / ADR-073 transports).

### 5.4 Sequencing — discover, centralize, cut over, retire

The migration sequence under the new doctrine extends UIAO_135 §4
(Systematic Specification Roadmap) with a new Priority 0 tier:

| Tier | Sequence | Deliverable |
|---|---|---|
| **P0 — Core DB stand-up** | Before any other plane is cut over | ADR-074 ratifies the operating store; UIAO_013 specifies the OrgPath core-DB binding; Azure SQL DB provisioned, Entra-only, schema v1.0 deployed |
| **P1 — Structural Completeness** *(carries forward from UIAO_135)* | Computer Object Transformation, HR-Agnostic Provisioning, Service Account → Workload Identity Mapping | Specs land with explicit core-DB writes |
| **P2 — Protocol & Infrastructure** *(carries forward from UIAO_135)* | Kerberos/NTLM Elimination *(ADR-068 + amendments)*, AD Sites → Named Locations, ADCS → Cloud PKI + CBA | Per-domain specs; each consumes the core DB |
| **P3 — Application Layer** *(carries forward from UIAO_135)* | AD Security Group Rationalization, LDAP-Dependent Application Migration | Per-domain specs |
| **P4 — Vendor SoR Demotion** *(new tier)* | Every vendor surface enumerated in §2.2 documents its status (SoR / cache / evidence) and its reconciliation path to the core DB | Per-vendor amendments to existing adapter contracts |
| **P5 — Stacked Persistence Retirement** *(new tier)* | Where stacked persistence existed only because no core DB was available (in-memory bundle joins, file-system claim caches), retire to the core DB | Per-subsystem migration tickets |

P0 is gating: nothing else proceeds until the core DB is stood up
and ADR-074 is accepted. This is the same gating posture ADR-073
applied to NAC ("Phase A lands the canon contract before any data
population").

## 6. OrgPath and OrgTree in the Core Operating Database

### 6.1 The canonical OrgTree table

The OrgTree currently lives in `canon/data/orgpath/codebook.yaml`
(UIAO_151) and is consumed by adapters at runtime via `importlib.
resources`. That posture is correct for canon: read-only, version-
controlled, anchored by ADR.

The expansion: the core operating DB carries a materialized
projection — `orgtree_node` — populated from the codebook by a
canon-sync job that runs on every canon-PR merge. The table is
read-mostly; writes occur only via the sync job.

| Column | Type | Source |
|---|---|---|
| `orgpath` | string (PK) | `codebook.yaml` `path` field |
| `display_name` | string | `codebook.yaml` `displayName` |
| `parent_orgpath` | string (FK self) | computed from path delimiters |
| `lifecycle_state` | enum (`active`, `unpositioned`, `decommissioning`, `retired`) | `codebook.yaml` `lifecycle` |
| `governance_owner` | string | `codebook.yaml` `owner` |
| `sla_class` | string | UIAO_162 SLA Heatmap projection |
| `provenance_sha256` | string (FK to `evidence_event`) | sync-job-emitted provenance |
| `synced_at` | timestamp | sync job |
| `canon_version` | string | `document-registry.yaml` version of UIAO_151 at sync time |

Every governed-object row (user, device, service principal, NAC
session, policy assignment) references `orgpath` as a foreign key
into this table. ADR-063's storage-slot binding (Entra
`extensionAttribute1`) and ADR-073's NAC enforcement payload point
*back* to this table by string match.

### 6.2 OrgPath as the join key everywhere

A worked example. Consider a single Conditional Access targeting
event: "Policy CA-FIN-RequireCompliant is targeted at dynamic group
OrgTree-FIN-Users, derived from canon UIAO_152 SHA-256 `a3f1...`,
written by managed identity `mi-uiao-orchestrator` at
2026-05-15T14:32:01Z."

Today this fact lives in:

- Entra (the CA policy assignment, retrievable via Graph)
- The Evidence Bundle (the in-memory bundle for the most recent
  orchestrator run)
- The canon YAML (`policy-targets.yaml`, declared)
- The substrate walker's transient memory (until it dumps a report)

Under the new doctrine, the fact lives in one row in the core DB,
table `ca_policy_assignment`:

| Column | Value |
|---|---|
| `assignment_id` (PK) | `ca-fin-require-compliant@OrgTree-FIN-Users` |
| `policy_name` | `CA-FIN-RequireCompliant` |
| `target_group_name` | `OrgTree-FIN-Users` |
| `target_orgpath` (FK) | `/CORP/US/FIN` |
| `transport` | `intune` / `azure-policy` / `nac` (per ADR-039 / ADR-073) |
| `intent` | `permit` / `quarantine` / `deny` |
| `canon_sha256` | `a3f1…` (UIAO_152 source hash) |
| `applied_by` | `mi-uiao-orchestrator` (Entra Managed Identity) |
| `applied_at` | `2026-05-15T14:32:01Z` |
| `apply_op` | `ca-assign-create` (from the ADR-073 op vocabulary, extended to CA via ADR-039) |
| `provenance_sha256` | content-hash of the apply receipt |

Other rows hold the Entra-side read-back (what Graph reports the
assignment is *right now*), and a drift-detection job compares
canonical vs. read-back. Disagreement is one of the five drift
classes.

`target_orgpath` is the join key. The same `orgpath` value joins:

- this row to `orgtree_node`
- this row to every `user` row whose `orgpath = /CORP/US/FIN/...`
- this row to every `device` row in the Finance branch
- this row to every `nac_session` row a Finance device produced
- this row to every `evidence_event` row that cites a Finance
  governance action

The substrate becomes queryable as a relational database. CQL
(UIAO_108) compiles to actual SQL.

### 6.3 Three transports → three writeback paths from one row

ADR-039 + ADR-073 declare three transports. Under the new doctrine,
each transport is a *writeback path* from one canonical row, not
three independent records of intent.

```
              core DB (one row per assignment)
                       │
       ┌───────────────┼───────────────┐
       │               │               │
   Intune writer  Azure Policy     NAC writer
   sub-adapter    sub-adapter      sub-adapter
       │               │               │
   Graph API      ARM API         AAA server API
   (Intune)       (Azure Policy)  (ISE/ClearPass/
                                   Entra RADIUS)
       │               │               │
   Intune profile  Policy assignment NAC policy-set
   on device       on Arc machine    on AAA server
                                     +
                                     RADIUS Access-Accept
                                     emits VLAN + dACL + SGT
                                     against the device session
```

The writer adapters share one provenance chain. Each writeback
attaches a `transport`, `vendor_endpoint`, and `apply_receipt_sha256`
to the core-DB row. Drift detection per-transport is a *read-back*
of the vendor surface compared to the canonical row.

This is what "OrgTree governs policy targeting stays one decision
rather than fragmenting into three" (ADR-073 §"Consequences /
Negative") looks like at the data layer: not three records sharing
naming, but one row with three writeback channels.

### 6.4 Cross-canon integrity becomes referential integrity

ADR-073 §D1 declares cross-canon integrity:

- `target_group` must resolve to a live UIAO_152 dynamic group.
- `enforcement.vlan_id` must resolve to a live VLAN in the IPAM canon.
- `(policy_ref, target_group, enforcement)` triple is unique.
- `assignment_name` is unique across the file.

Today these are loader checks against YAML files. Under the new
doctrine, they become database-level constraints:

- `FOREIGN KEY (target_group_name) REFERENCES dynamic_group(name)`
- `FOREIGN KEY (vlan_id) REFERENCES ipam_vlan(vlan_id)` (the IPAM
  vendor SoR's relevant rows projected into a `ipam_vlan` mirror
  table on the canon-sync schedule)
- `UNIQUE INDEX (policy_ref_value, target_group_name, vlan_id, dacl_name, sgt_tag, posture_profile)`
- `UNIQUE INDEX (assignment_name)`

The substrate walker shifts from *running YAML loader checks* to
*reading database constraint violations from the CDC log*.
Constraint violations cannot occur at runtime under normal writes;
they can only occur during canon-PR merge if the canon-sync job
attempts a write that violates an existing constraint. The walker
reports the constraint name, the offending row, and the canon-PR
that introduced it.

## 7. Session-to-Tagged-Network-Security in the Core Operating Database

This section is the load-bearing connection the user named.
"Session-to-Tagged-Network-Security" is the *moment* when an 802.1X
session, an SGT/VLAN/dACL enforcement payload, and an OrgPath
attribution converge into one governance claim. Without a canonical
place to land that claim, the moment is recorded N times (in the
AAA server, in the switch, in the SIEM, in the EDR, in the
substrate's transient memory) and reconciled never.

### 7.1 What ADR-073's NAC contract produces

ADR-073 §"Decision" specifies what flows out of the substrate into
the AAA server:

```yaml
nac_assignments:
  - assignment_name: nac-fin-corp-endpoint
    aaa_server: cisco-ise
    policy_ref:
      kind: policy-set
      match_by: name
      value: NAC-FIN-CorpEndpoint
    target_group: OrgTree-FIN-Devices
    enforcement:
      vlan_id: 142
      dacl_name: dACL-FIN-Standard
      sgt_tag: 16
      posture_profile: Posture-CorpEndpoint-Standard
      change_of_authorization: true
    intent: permit
    gcc_boundary: gcc-moderate
```

What ADR-073 does *not* specify: the per-session evidence record
produced when a device 802.1X-authenticates against this binding.
The AAA server's session table holds the record; the substrate
treats the AAA server as authoritative; *but the substrate has no
canonical row* for the resulting session-tagged-network-security
claim.

This is the second-most-load-bearing gap in the current state (after
the substrate's missing operating store). It is what the operator
hits when they ask: "Did the device `wks-fin-042` actually land on
VLAN 142 with dACL-FIN-Standard at the time the FIN-OrgPath user
logged in this morning?" Today the answer is "look across ISE's
session table, the switch's port-log, the SIEM's RADIUS-accounting
log, the EDR's connection record, and the Intune compliance state,
and stitch them together by MAC address and timestamp." That is a
forensic exercise. It is not continuous governance.

### 7.2 Session record schema (tagged-network-session)

The expansion: a `tagged_network_session` table in the core
operating DB.

| Column | Type | Source | Notes |
|---|---|---|---|
| `session_id` (PK) | UUID | AAA accounting `Acct-Session-Id` | Vendor-provided; substrate-stable |
| `device_id` (FK to `device`) | string | Entra device object id | resolved from cert SAN OtherName or MAC↔cert lookup |
| `device_orgpath` (FK to `orgtree_node`) | string | core DB `device.orgpath` snapshot at session start | the *substrate's* canonical OrgPath; if cert claims a different OrgPath, that is `DRIFT-IDENTITY` |
| `user_id` (FK to `user`, nullable) | string | EAP-TLS supplicant identity if present | null for pre-user-logon device authentication |
| `user_orgpath` (FK to `orgtree_node`, nullable) | string | core DB `user.orgpath` at session start | |
| `aaa_server` | enum (`cisco-ise`, `aruba-clearpass`, `entra-radius`, `nps`) | per ADR-073 §D1 | which AAA decided |
| `nac_assignment_id` (FK) | string | the `assignment_name` from `nac_assignments[]` that matched | one assignment per session |
| `applied_vlan_id` (FK to `ipam_vlan`) | int | RADIUS `Tunnel-Private-Group-ID` | the actual VLAN returned by AAA |
| `applied_dacl_name` | string (nullable) | RADIUS `Filter-ID` / `Cisco-AVPair:ACS:dACL-name` | |
| `applied_sgt_tag` | int (nullable) | RADIUS `Cisco-AVPair:cts:security-group-tag` | |
| `applied_posture_profile` | string (nullable) | AAA accounting posture state | |
| `change_of_authorization_count` | int | AAA CoA event count | re-evaluation triggers (Intune compliance change, etc.) |
| `session_state` | enum (`active`, `quarantine`, `terminated`) | AAA accounting | derived from Start / Stop / Interim-Update |
| `started_at` | timestamp | AAA Acct-Status-Type:Start | |
| `last_seen_at` | timestamp | AAA Interim-Update | |
| `terminated_at` | timestamp (nullable) | AAA Stop | |
| `cert_sha256` | string | device cert presented at session start | for re-enrollment / replay detection |
| `provenance_sha256` | string | content-hash of the accounting record | immutable audit anchor |

This is the canonical row. Every AAA vendor's session table is now
a *cache* — operational scratch the vendor uses internally and from
which the substrate ingests via the AAA adapter's accounting feed.

### 7.3 The single DB becomes the canonical AAA evidence store

Three properties follow from §7.2:

1. **One row, four planes.** The same `tagged_network_session` row
   has joins into `device` (Intune-First plane), `user` (Entra
   identity plane), `nac_assignment` (ADR-073 governance plane),
   and `ipam_vlan` (BlueCat / Infoblox plane). Cross-plane queries
   resolve in one SQL statement against the core DB rather than via
   N adapter round-trips.
2. **Drift on session evidence.** A session whose `applied_vlan_id`
   does not match the `nac_assignments[]` declared
   `enforcement.vlan_id` for the session's matched policy_ref is a
   `DRIFT-SEMANTIC` finding — the AAA server returned something
   other than what canon declared. A session whose `device_orgpath`
   in the substrate disagrees with the OrgPath the cert SAN
   OtherName presented is `DRIFT-IDENTITY`. A session for an
   `nac_assignment_id` that no longer exists in canon is
   `DRIFT-PROVENANCE`. A session whose state-transition history
   shows enforcement-changes without canon-side authorization is
   `DRIFT-AUTHZ`. All four classes apply at the row level.
3. **Audit assembly is one query.** "Show every session for OrgPath
   `/CORP/US/FIN` in the last 24 hours where applied VLAN differed
   from canon" is one SQL statement. "Show every session whose
   device's Intune compliance state was non-compliant at session
   start" is one join (Intune compliance state lives in another
   core-DB table, projected from the Intune adapter's read).
   Continuous-monitoring evidence becomes a SELECT, not a forensic
   exercise.

### 7.4 SGT, VLAN, dACL as foreign keys into the core DB

The `applied_vlan_id`, `applied_sgt_tag`, `applied_dacl_name`, and
`applied_posture_profile` columns reference canonical projections of
vendor SoRs:

| Column | References | Source of truth |
|---|---|---|
| `applied_vlan_id` | `ipam_vlan(vlan_id)` | BlueCat / Infoblox IPAM SoR; mirrored into the core DB via IPAM adapter on canon-sync schedule |
| `applied_sgt_tag` | `sgt_registry(sgt_id)` | Cisco TrustSec SGT registry; mirrored from ISE via ERS API; ADR-073 §"Open" defers whether SGT-only targeting deserves a fourth transport — until then SGT rides with the NAC assignment |
| `applied_dacl_name` | `nac_dacl_inventory(dacl_name, aaa_server)` | AAA-server-side inventory; mirrored via the AAA adapter's read path |
| `applied_posture_profile` | `posture_profile_inventory(profile_name, aaa_server)` | Same |

The cross-references are *materialized*, not just modeled — the
mirror tables hold actual rows so the foreign-key constraint is
enforced at write. If the AAA accounting feed delivers a session
referencing a VLAN that no longer exists in IPAM canon, the insert
fails and the substrate walker fires `DRIFT-PROVENANCE`. If the
session references an SGT that ISE has retired, same. The
constraint catches the failure on the *write* path rather than at
the next walk.

### 7.5 Drift on tagged-network-session vs. vendor session table

The vendor session tables (ISE, ClearPass, NPS) remain operational —
nothing in the new doctrine attempts to displace them. What changes:

- The AAA adapter's read-path now writes one row to
  `tagged_network_session` per session-state transition observed in
  the vendor accounting feed.
- A reconciliation job ("session-evidence reconcile") compares the
  vendor session table state against the core DB at regular
  intervals (default: 5 minutes during business hours, 1 hour
  otherwise). Disagreement → `DRIFT-PROVENANCE` (substrate is
  missing a session the vendor has) or `DRIFT-SEMANTIC` (vendor
  reports a different enforcement payload than canon).
- The vendor session table is treated as ephemeral: rows expire on
  the vendor side per the vendor's TTL (typically 24 hours of
  inactivity for ISE). The core DB row is permanent; it is the
  audit anchor.

The pattern is identical to the OrgPath read-back pattern from
ADR-063: vendor surface reflects what canon wrote; substrate
periodically reads the reflection back; disagreement is drift.

## 8. Vendor Strategy Implications

### 8.1 Vendor classification — SoR-permitted vs. cache-only

The expansion adds a vendor-classification column to
`modernization-registry.yaml` and `adapter-registry.yaml`. Each
adapter declares one of:

| Classification | Meaning | Examples |
|---|---|---|
| `sor-permitted` | Vendor is SoR for facts the substrate does not author; substrate consumes and joins on OrgPath | Entra ID (identity), ARM (Azure resources), BlueCat/Infoblox (IP/VLAN/DNS), HR (employment), AD CS / Cloud PKI (cert inventory), Purview (data-asset lineage) |
| `cache` | Vendor reflects facts the substrate authors; substrate writes outward and reads back for drift detection | ServiceNow CMDB (OrgPath on CIs), ISE/ClearPass (NAC assignments), Intune (OrgTree-* configuration profile bindings), Azure Policy (Arc OrgPath assignments) |
| `evidence` | Vendor produces telemetry / events the substrate joins by OrgPath at query time | Defender suite, Sentinel, Cloud App Security, Microsoft Graph audit logs, Palo Alto NGFW logs |
| `governance-input` | Vendor produces findings the substrate consumes into its evidence chain; not SoR for any substrate-owned fact | ScubaGear, SailPoint NER, vulnerability scanners, FedRAMP CR-26 catalog |

A vendor adapter without a classification fails CI under the new
schema. A vendor adapter claiming `sor-permitted` for a fact the
substrate also claims as substrate-owned is a
`DRIFT-PERSISTENCE::stacked-sor` finding.

### 8.2 Microsoft surfaces — Graph as the canonical event stream

Microsoft Graph already exposes a uniform event surface across
Entra, Intune, Defender, Purview, and SharePoint / OneDrive /
Exchange. Under the new doctrine:

- **Entra writes (`extensionAttribute1`, group membership, AU
  assignments)** go through Graph and land back into the core DB
  via the `EntraAdapter` read-path.
- **Intune writes (configuration profile assignments, compliance
  policies)** go through Graph and similarly read back.
- **Defender and Purview reads** are streaming-event-shaped via
  Graph or Event Hub; the core DB ingests via the SIEM adapter and
  joins at query time.
- **The `mcp__github__*` and `_graph_clouds.py` resolution patterns**
  already canonicalize how Graph endpoints resolve per cloud
  (commercial / GCC-High / DoD); the core DB connection inherits
  this resolution.

Microsoft Graph is the canonical event bus for everything
identity-anchored. The substrate does not duplicate it; it
*projects* from it into the core DB.

### 8.3 BlueCat / Infoblox — IPAM SoR retains DB, exposes via webhook

The IPAM vendors retain their DBs as SoR for IP, VLAN, and DNS
allocations. What changes:

- Both vendors expose change events (Infoblox NIOS Outbound API,
  BlueCat BAM webhook). The IPAM adapter subscribes to these and
  mirrors the relevant rows (`ipam_vlan`, `ipam_subnet`, `ipam_record`)
  into the core DB.
- The mirror is read-mostly; the substrate does not write back to
  IPAM (UIAO does not claim authority over IP allocation).
- The mirror is the foreign-key target for `tagged_network_session.
  applied_vlan_id` and `nac_assignments[].enforcement.vlan_id`.

This is exactly the pattern the OrgPath narrative chapter 14
("OrgPath with Third-Party DDI") already develops at the policy
layer. The expansion is mechanical: the canonical projection lives
in the core DB.

### 8.4 ServiceNow CMDB — cache, not SoR for identity/OrgPath

ServiceNow is the agency's IT service management SoR. It is *not*
the SoR for OrgPath on a CI. Under the new doctrine:

- The ServiceNow adapter writes `u_uiao_orgpath` (canonical custom
  attribute) on every CI record from the core DB's authoritative
  row.
- The CI record reflects OrgPath as a *cache*; ServiceNow workflows
  (ticket routing, change advisory board scoping, incident
  assignment) read this cached value.
- A change to OrgPath on a CI made directly in ServiceNow is a
  `DRIFT-AUTHZ` finding — unauthorized writer.

ServiceNow remains SoR for IT service management process state
(tickets, changes, incidents, problems). The substrate does not
attempt to displace this.

### 8.5 SailPoint NER — SoR for risk only, OrgPath written back

ADR-059 (SailPoint adapter family) already establishes SailPoint
NER as a FedRAMP Moderate (commercial-exception) component for
non-employee risk. The new doctrine confirms:

- SailPoint is SoR for *risk score* and *entitlement review evidence*.
- SailPoint is *not* SoR for OrgPath, identity attributes, or
  access lifecycle workflow state — Entra ID Governance owns those.
- The SailPoint adapter writes OrgPath into the NER identity record
  on every reconciliation cycle (cached from the core DB).
- Risk scores flow back into the core DB as a `risk_score` table
  joined to `user` and `non_employee` rows.

### 8.6 Cisco ISE / Aruba ClearPass — policy authoring SoR, session evidence to UIAO

The AAA platforms remain the policy authoring surface. ADR-073
already declares the *binding* (assignment) is canonical in UIAO,
the *body* (policy set, service, posture profile) is authored on
the AAA platform. The new doctrine adds:

- Each platform's session table is operational scratch.
- Each platform emits accounting records into the core DB's
  `tagged_network_session` via the AAA adapter.
- Each platform's policy-set / service inventory is mirrored into
  the core DB on canon-sync schedule for foreign-key resolution.

### 8.7 Defender / Sentinel — telemetry only, identity references resolved at query time

The Defender suite and Sentinel are evidence sinks. The new
doctrine does not change their role:

- Defender for Endpoint / Identity / Cloud Apps / Servers consume
  the core DB's `device` and `user` tables to resolve OrgPath at
  ingestion time.
- Sentinel KQL queries reference the core DB via the SIEM adapter's
  query layer (or via Fabric SQL mirror for analytic workloads).
- Neither product is SoR for any substrate-owned fact; both join
  by OrgPath at query time.

## 9. Proposed Canonical Actions

This section enumerates the canon-PR work the expansion requires.
Each item is sized for one PR with one ADR.

### 9.1 ADR-074 — Single Core Operating Database Doctrine

**Status:** Proposed. **Supersedes:** none. **Amends:** UIAO-SSOT
(UIAO_001) §"Drift baseline" to add `DRIFT-PERSISTENCE`; UIAO_109
to anchor the data-lake zones to the new operating store; ADR-073
§"NAC sub-adapter" to land session evidence in
`tagged_network_session`.

**Decision sketch:**

1. The UIAO substrate operates against a single canonical
   relational store: an Azure SQL Database instance in the
   GCC-Moderate boundary, Entra-only authentication.
2. The store holds every substrate-authored operating fact —
   OrgPath bindings, policy assignments, NAC sessions, drift
   findings, evidence events.
3. Vendor SoRs are demoted to `sor-permitted` (for vendor-owned
   facts), `cache` (for substrate-owned facts), `evidence` (for
   telemetry), or `governance-input` (for findings) per a new
   classification column on the adapter registries.
4. A new drift sub-class `DRIFT-PERSISTENCE::stacked-sor` fires
   when a vendor surface is treated as authoritative for a fact the
   core DB owns.
5. Schema lifecycle: schema v1.0 lands with the ADR; subsequent
   schema changes are governed by per-version migration ADRs.
6. Backup, geo-replication, retention, and disaster recovery
   follow Azure SQL DB defaults plus FedRAMP Moderate requirements.

### 9.2 UIAO_013 — OrgPath in the Core Operating Database

A new canonical artifact in the `UIAO_010` / `UIAO_011` / `UIAO_012`
family — the fourth transport in the OrgPath series. **Allocation:**
UIAO_013 (next slot after UIAO_012; consistent with the
"OrgPath in X" naming pattern). **Title:** "OrgPath in the Core
Operating Database & Substrate Persistence Layer".

**Outline:**

- Scope: substrate-authored facts vs. vendor-owned facts.
- The canonical schema (§6.1 + §6.2 of this research).
- The four read-back targets (Entra `extensionAttribute1`, ARM tag,
  device cert SAN, AAA enforcement payload) and the canonical
  drift surface.
- The three writeback paths (Intune, Azure Policy, NAC) as
  channels off one row.
- The session-evidence schema (§7).
- Cross-canon integrity → referential integrity (§6.4).
- Operator workflows: schema migration, canon-sync, drift
  reconciliation.

UIAO_013 is the operator-facing narrative; ADR-074 is the
doctrinal anchor.

### 9.3 UIAO_109 v2.0 — Data Lake anchored to the Core Operating Store

**Amendment** to UIAO_109 (currently v1.0). The amendment adds a
"Section 0: Operating Store" that declares:

- The Compliance Data Lake's three zones (Raw / Normalized /
  Curated) are *projections* of the core operating database
  (Section 0).
- The Raw zone retains vendor-shaped artifacts (Defender exports,
  ScubaGear JSON / CSV, Sentinel KQL results) as immutable
  evidence.
- The Normalized zone is materialized from the operating DB via
  Fabric mirroring (per OrgPath narrative chapter 07a).
- The Curated zone holds analytical views over the Normalized
  zone — KSI evaluations, control status views, POA&M views, OSCAL
  exports.

The amendment preserves UIAO_109's hash + provenance per-object
requirement; it adds CDC streaming from the operating store as the
canonical mechanism that produces the per-object hashes.

### 9.4 Extension of ADR-068 — Auth modernization beyond SQL Server

ADR-068's scope statement defers broader auth modernization to a
future ADR. ADR-074 inherits that work. The amendment to ADR-068
adds:

- A "References ADR-074" line in the cross-reference list.
- A note in §"Decision" that the three canonical positions (NTLM
  deprecation, Cloud Kerberos trust, Entra CBA) apply to *every*
  DB-bearing surface UIAO consumes, not just SQL Server. SQL
  Server (Spec3-D1.8) is the reference path; every other workload
  (file servers, print servers, line-of-business apps, the
  substrate's own core DB) inherits the same sequence.

### 9.5 Extension of UIAO_135 — Data-Plane Transformation Row

UIAO_135 §1.2 currently names "SQL Server Authentication — Service
Identity" as transformation 7 — the only data-plane row in the
inventory. The amendment adds:

| # | Transformation | Source (Legacy) | Target (Modern) | UIAO Source |
|---|---|---|---|---|
| 7a | **Substrate Operating Store — Canonical Persistence** | File-system bundles + JSON evidence + transient orchestrator memory; no canonical operating database | Azure SQL Database (Entra-only auth, GCC-Moderate boundary) per ADR-074; Fabric SQL mirror for analytics | ADR-074, UIAO_013 |
| 7b | **Vendor SoR Demotion** | Each vendor surface implicitly authoritative for facts it touches | Each vendor classified `sor-permitted` / `cache` / `evidence` / `governance-input` per ADR-074; substrate-owned facts live in the core DB only | ADR-074 §"Vendor classification" |
| 7c | **Tagged-Network-Session Evidence** | Vendor-private session tables (ISE, ClearPass, NPS); no canonical row | One row per session in `tagged_network_session`; vendor tables are operational scratch | ADR-073, ADR-074, UIAO_013 |

§3.2 ("Partially Defined") loses the broader-auth gap line (closed
by the ADR-068 amendment). §3.3 ("Not Yet Defined") loses nothing —
the AD Sites / Subnets and AD CS rows remain open, gated on
implementation, not specification.

### 9.6 Extension of DM_090 — Workload → Substrate bridge

DM_090 (the SQL Server workload adapter) gains a §"Substrate
Integration" section declaring:

- The migrated SQL Server instances *the agency operates* are
  governed by DM_090's existing contract.
- The SQL instance the *substrate operates as its core DB* is
  governed by ADR-074, *not* DM_090.
- A bridge: migrated agency SQL instances may register their
  service-account principal's OrgPath, host-machine OrgPath, and
  SPN inventory into the core DB via the SQL workload adapter's
  evidence-emission path. This makes the migrated estate
  queryable alongside substrate-owned operating facts.

### 9.7 New drift sub-class — `DRIFT-PERSISTENCE::stacked-sor`

A sixth drift sub-class added to UIAO-SSOT (UIAO_001) §"Drift
baseline" and to `docs/docs/16_DriftDetectionStandard.qmd`:

| Class | Means |
|---|---|
| `DRIFT-PERSISTENCE` | Substrate-owned fact appears with conflicting authority in two stores |
| `DRIFT-PERSISTENCE::stacked-sor` | A vendor surface other than the core operating database is treated as authoritative for a substrate-owned fact |

Sub-class detection: at canon-PR merge, the substrate walker
inspects every adapter registry entry for the classification field
introduced by ADR-074. An adapter declaring `sor-permitted` for a
fact also claimed by the core DB schema emits the finding.

ADR-063's deferred `DRIFT-SCHEMA::slot-occupied` sub-class is
re-anchored here as part of the same drift-sub-classing pass.

## 10. Risks, Opens, and Sequencing

### 10.1 Risks — and the compensating canon

| Risk | Compensating canon | Residual exposure |
|---|---|---|
| Azure SQL DB single-region failure | Geo-redundant active-passive replica in a paired region; Azure Backup vault with PITR; immutable CDC stream to Sentinel | Brief read-availability window during failover; write availability degraded; FedRAMP Moderate continuity met by replica |
| Entra-only auth — what if the Entra tenant itself is degraded? | The substrate's break-glass account (Entra Privileged Identity Management) has PIM-eligible `db_owner`; ADR-068 §"CBA rollout — privileged accounts first" applies | A full Entra outage degrades the substrate to read-only against the geo-replica; this is acceptable for the substrate's role |
| Lock-in to Azure SQL DB | The schema is portable to any PostgreSQL or SQL Server 2022+ target; ADR-074 records the schema as canon, not the vendor; reversibility is the same as for any Azure-anchored substrate component | Reversibility cost is bounded by schema migration, not by data export (CDC stream is portable) |
| Schema-migration drift | Per-version migration ADRs; schema lifecycle gated by canon-sync job; CI tests check schema-version compatibility | Migrations are versioned and reversible; backward-incompatible changes require an ADR |
| Stacked-SoR detection false-positives | The classification on each adapter is canon; vendor adapter must declare it; substrate walker only fires on conflict, not on adapter presence | Some legitimate edge cases (e.g., HR system writing employment attributes that propagate through Entra) need explicit `sor-permitted` declaration |
| Vendor pushback — vendors prefer to be SoR | ADR-074 names the SoR boundaries explicitly; vendor adapter contracts make the demotion enforceable; the substrate's enforcement is at *its own* layer, not at the vendor's | Vendor product roadmaps may not align with the demotion; the substrate's drift findings make non-alignment visible but do not prevent the vendor from continuing to assert SoR claims in marketing |
| Performance — adapter writes synchronously to the core DB | Adapter write-path is async-by-default via a write queue; backpressure handled by adapter retry (`retry.py`); the canon-sync job is the only synchronous writer | Write-queue depth is a tracked metric; SLA defined in UIAO_162 SLA Heatmap |

### 10.2 Opens — questions for governance review

1. **Tenant boundary.** Does the core operating database serve one
   tenant per UIAO deployment, or does a multi-tenant deployment
   (e.g., HRIT productization per ADR-058) share one DB with
   per-tenant row-level security? UIAO_201 workspace contract
   leans single-tenant; ADR-074 should follow that lean unless
   ADR-058 multi-tenancy requires otherwise.
2. **Schema authority.** Is the core DB schema canonized at
   `src/uiao/canon/schemas/operating-store/`, or at a sibling
   `src/uiao/db/` module? UIAO_201 invariants say canon ships as
   package data; the schema is canon, so it ships under
   `src/uiao/canon/` — but DDL is not a JSON Schema, so the schema
   structure needs an ADR-074 sub-decision.
3. **CQL → SQL.** UIAO_108 specifies CQL as "SQL-like queries over
   bundles." Does CQL remain a separate language with a SQL
   transpiler, or does the substrate accept SQL directly? Operator
   ergonomics favor keeping CQL; performance favors raw SQL.
   ADR-074 §"CQL execution" should specify.
4. **Fabric SQL mirror — read-only or writeable for analytical
   joins?** OrgPath narrative chapter 07a treats Fabric SQL as the
   data-plane SSOT. The mirror should be read-only by default; a
   future ADR may carve a writeable analytic-output zone.
5. **Stacked-SoR retro-finding policy.** The new drift sub-class
   `DRIFT-PERSISTENCE::stacked-sor` will produce a large initial
   backlog from the existing adapter graph. Does the substrate
   walker block CI on this backlog from day one, or does ADR-074
   include a grace window (e.g., warn-only until 2026-Q4) — same
   shape as ADR-073's Phase A → Phase C ramp?
6. **Encryption-at-rest of OrgPath history.** Always Encrypted on
   OrgPath columns is one option; the cost is operator ergonomics
   (every query must round-trip through the column encryption
   driver). ADR-074 should specify which columns are encrypted and
   on what key authority (Azure Key Vault, Managed HSM).

### 10.3 Sequencing — which canon edits land in which order

| Order | Canon edit | Blocking? |
|---|---|---|
| 1 | ADR-074 (this expansion's anchor) — Single Core Operating Database Doctrine | Yes — gates all subsequent items |
| 2 | UIAO_013 — OrgPath in the Core Operating Database | Companion to ADR-074 |
| 3 | UIAO_109 v2.0 amendment — anchor data lake to operating store | Companion; lands with ADR-074 |
| 4 | UIAO_001 (UIAO-SSOT) §"Drift baseline" amendment — add `DRIFT-PERSISTENCE` | Companion; lands with ADR-074 |
| 5 | `docs/docs/16_DriftDetectionStandard.qmd` amendment — drift sub-class table | Companion |
| 6 | `adapter-registry.yaml` + `modernization-registry.yaml` schema amendment — add `vendor-classification` column | Follows ADR-074; one PR |
| 7 | ADR-068 amendment — auth modernization scope expansion | Follows ADR-074 |
| 8 | UIAO_135 amendment — add transformations 7a / 7b / 7c | Follows ADR-074 |
| 9 | DM_090 amendment — workload → substrate bridge section | Follows ADR-074 |
| 10 | Per-adapter PRs adding `vendor-classification` declarations | Follows item 6; one PR per adapter family (Microsoft Graph adapters, IPAM adapters, AAA adapters, IGA adapters, ITSM adapters, telemetry adapters) |
| 11 | Schema v1.0 deployment + Azure SQL DB provisioning | Follows ADR-074; one infrastructure PR |
| 12 | Adapter write-path retrofits — adapters begin writing into the core DB | Per-adapter; non-blocking on §11 if the adapter declares evidence-only |
| 13 | Substrate walker — new `DRIFT-PERSISTENCE::stacked-sor` check | Follows item 6 |
| 14 | CQL → SQL execution path (UIAO_108 amendment) | Follows item 11 |
| 15 | Fabric SQL mirror activation | Follows item 11 |

The sequencing follows the same pattern ADR-073 established for
NAC: contract first, schema-constraint warn-only, data population,
schema-constraint blocking. The substrate has done this once
already; the second time costs less.

## Appendix A — Citation Index

The artifacts this research draws on, by section, for reviewer
convenience:

- §1.1 — UIAO_135 §1.2 row 7; Spec3-D1.8; DM_090; ADR-068; Spec3-D1.1.
- §1.2 — ADR-047, ADR-073, `bluecat_adapter.py`, `infoblox_adapter.py`,
  `paloalto_adapter.py`, `cyberark_adapter.py`, `servicenow_adapter.py`,
  `siem_adapter.py`, `stigcompliance_adapter.py`.
- §1.3 — DM_090, OrgPath narrative chapter 07a.
- §1.4 — UIAO_109 (data lake), UIAO_108 (CQL), UIAO_113 (evidence
  graph), `database_base.py`.
- §1.5 — OrgPath narrative chapter 07a, federal-ssot-alignment
  whitepaper.
- §2 — federal-ssot-alignment whitepaper §1; UIAO-SSOT §"Drift
  baseline"; charter CHARTER-003 (SSOT vs SoA).
- §3 — UIAO-SSOT, UIAO_109, DM_090, `database_base.py`.
- §4 — ADR-063, ADR-073, OrgPath narrative chapter 07a.
- §5 — ADR-068, ADR-063, UIAO_135 §4, ADR-004, ADR-003.
- §6 — UIAO_151 codebook, ADR-073, ADR-039, ADR-036, ADR-037,
  UIAO_152, UIAO_154.
- §7 — UIAO_012, ADR-073, ADR-047, UIAO_153.
- §8 — ADR-059 (SailPoint), `adapter-registry.yaml`,
  `modernization-registry.yaml`, OrgPath narrative chapter 14
  (third-party DDI).
- §9 — UIAO-SSOT, UIAO_109, UIAO_135, DM_090, ADR-063, ADR-068,
  ADR-073, document-registry.yaml (UIAO_013 allocation), adr-index
  (ADR-074 allocation).
- §10 — UIAO_201 workspace contract, UIAO_162 SLA Heatmap,
  ADR-058 (HRIT multi-tenancy), UIAO_108 (CQL).

## Appendix B — Relationship to existing modernization narrative

The customer-facing modernization narrative (the seven-chapter
UIAO Modernization Program at
[`docs/customer-documents/modernization/uiao-modernization-program/`](../../../docs/customer-documents/modernization/uiao-modernization-program/))
intersects this research at three points:

1. **Phase 0 — Foundation.** The program overview describes OrgPath
   establishment as the first deliverable. Under the new doctrine,
   Phase 0 also includes core-DB stand-up — schema v1.0 deployed
   and Entra-only auth verified before any Phase 1 work begins.
2. **Phase 2 — Governance OS.** The Phase 2 chapter
   ([`03-phase2-governance-os.qmd`](../../../docs/customer-documents/modernization/uiao-modernization-program/03-phase2-governance-os.qmd))
   describes drift detection and SCuBA integration. Under the new
   doctrine, drift findings land as rows in the core DB; ScubaGear
   evidence is ingested via the Raw zone and joined to OrgPath at
   the Normalized zone projection.
3. **Phase 4 — Multi-Agent.** Multi-agent governance
   ([`05-phase4-multi-agent.qmd`](../../../docs/customer-documents/modernization/uiao-modernization-program/05-phase4-multi-agent.qmd))
   presumes a shared substrate. The core DB is that substrate —
   every agent reads canonical rows, writes via the same write
   queue, and produces evidence into the same chain.

The customer narrative does not need to change in this PR. The
canon edits in §9 land first; the customer narrative receives a
follow-on PR that incorporates the new doctrine into the program
chapters.

## Appendix C — What the agent author looked at

This research was produced by reading the following files
end-to-end and the following query patterns across the corpus.
Recorded so reviewers can verify coverage:

- `src/uiao/canon/UIAO-SSOT.md`
- `src/uiao/canon/UIAO_007_OrgTree_Modernization_AD_to_EntraID_v1.0.md`
- `src/uiao/canon/UIAO_010_OrgPath_in_Azure_Policy.md`
- `src/uiao/canon/UIAO_011_OrgPath_in_Intune_and_Device_Governance.md`
- `src/uiao/canon/UIAO_012_OrgPath_in_NAC_and_8021X.md`
- `src/uiao/canon/UIAO_135_identity-directory-transformation-inventory.md`
- `src/uiao/canon/specs/data-lake.md`
- `src/uiao/canon/adr/adr-063-orgpath-storage-slot-binding.md`
- `src/uiao/canon/adr/adr-068-kerberos-ntlm-elimination.md`
- `src/uiao/canon/adr/adr-073-policy-targeting-nac-third-transport.md`
- `src/uiao/modernization/directory-migration/adapters/sql-server/sql-server-adapter-interface.md`
- `src/uiao/adapters/database_base.py`
- `docs/customer-documents/orgpath-narrative/07a-uiao-beneath-the-azure-ssot-stack.qmd`
- `docs/customer-documents/whitepapers/federal-ssot-alignment.qmd`
- `docs/customer-documents/modernization/uiao-modernization-program/00-program-overview.qmd`
- corpus grep across `src/uiao/canon/`, `docs/`, `src/uiao/adapters/`,
  `src/uiao/modernization/`, `tests/`, `inbox/`, `phase2/`,
  `diagrams/` for: `SQL`, `sql server`, `mssql`, `t-sql`, `azure sql`,
  `sqlite`, `postgres`, `mysql`, `cosmos`, `database`, `OrgPath`,
  `OrgTree`, `SSOT`, `centralization`, `entra`, `Active Directory`,
  `single core database`, `stacked database`, `BlueCat`, `Infoblox`,
  `ServiceNow`, `SailPoint`, `Sentinel`, `Defender`, `Intune`,
  `evidence store`, `IR backing`, `audit store`, `tagged network`,
  `SGT`, `TrustSec`, `VLAN`.

The corpus search was performed by a delegated `Explore` agent; its
returned inventory is preserved in the conversation transcript for
this branch.
