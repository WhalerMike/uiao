# AD→OrgTree/OrgPath Integration Blueprint

**Enterprise Identity Architecture & Hierarchical Lineage Derivation**

+--------------+--------------------------------------+-----------------------+--------------------------+
| **Version:** | **1.0**                              | **Status:**           | **Implementation-Ready** |
+==============+======================================+=======================+==========================+
| **Date:**    | **May 7, 2026**                      | **Classification:**   | **Internal ---           |
|              |                                      |                       | Confidential**           |
+--------------+--------------------------------------+-----------------------+--------------------------+
| **Author:**  | **Enterprise Architecture & IAM      | **Audience:**         | **Engineering, SRE, IAM, |
|              | Engineering**                        |                       | AD Operations**          |
+--------------+--------------------------------------+-----------------------+--------------------------+
| **Scope:**   | **Active Directory (authoritative identity source) → OrgTree structural layer → OrgPath |
|              | lineage derivation → Downstream system readiness**                                      |
+--------------+-----------------------------------------------------------------------------------------+

+----------------------------------------------------------------------+
| ## Table of Contents                                                 |
|                                                                      |
| > 1\. Executive Summary                                              |
| >                                                                    |
| > 2\. Integration Architecture Overview 2.1 Component Map 2.2 Data   |
| > Flow Summary                                                       |
| >                                                                    |
| > 3\. AD Source Schema --- Canonical Object Taxonomy 3.1 Object      |
| > Classes Ingested 3.2 Core AD Attributes --- User Object 3.3 Core   |
| > AD Attributes --- OU Object 3.4 Core AD Attributes --- Group       |
| > Object                                                             |
| >                                                                    |
| > 4\. OrgTree Schema Definition 4.1 OrgNode --- Canonical Record 4.2 |
| > OrgTree Graph Model 4.3 Closure Table Schema                       |
| >                                                                    |
| > 5\. OrgPath Specification 5.1 OrgPath Format 5.2 OrgPath           |
| > Derivation Algorithm 5.3 OrgPath Cache Invalidation 5.4 OrgPath    |
| > Versioning                                                         |
| >                                                                    |
| > 6\. Attribute Inheritance Propagation 6.1 Inheritance Model 6.2    |
| > Inheritable Attribute Catalog 6.3 Inheritance Resolution Algorithm |
| >                                                                    |
| > 7\. Lifecycle State Machine 7.1 States 7.2 Lifecycle Transition    |
| > Rules 7.3 Lifecycle Event Payload Schema                           |
| >                                                                    |
| > 8\. Drift Detection Engine 8.1 Drift Definition 8.2 Drift          |
| > Categories 8.3 Drift Detection Cycle 8.4 Drift Alert Schema        |
| >                                                                    |
| > 9\. Group Ingestion & Role Mapping 9.1 Group Type Resolution 9.2   |
| > Membership Flattening 9.3 Role-to-OrgPath Inference                |
| >                                                                    |
| > 10\. Downstream Readiness 10.1 Consuming Systems Registry 10.2     |
| > Entra ID Sync Field Mapping 10.3 Consumer Event Contract           |
| >                                                                    |
| > 11\. Implementation Runbook 11.1 Pre-Flight Checklist 11.2 Key     |
| > Configuration Reference                                            |
| >                                                                    |
| > 12\. Governance, Security & Compliance 12.1 Data Sensitivity       |
| > Classification 12.2 RBAC Model for OrgTree API 12.3 Audit Trail    |
| > Requirements                                                       |
| >                                                                    |
| > 13\. Reference: Key Formulas & Identifiers 13.1 Unique Key Summary |
+----------------------------------------------------------------------+

## 1. Executive Summary

This blueprint defines the complete integration path from **Active
Directory (AD)** as the authoritative identity and organizational source
into the **OrgTree** hierarchical model and **OrgPath** lineage
derivation system. It is intended as an immediately actionable
engineering handoff document for implementing, validating, and operating
this integration in a production enterprise environment.

Active Directory remains the system of record for all identity and
organizational unit (OU) data within the enterprise. The integration
defined herein ingests, normalizes, and transforms that data into a
canonical, versioned, graph-backed OrgTree structure from which
human-readable and machine-parseable OrgPath strings are derived.
Downstream systems --- including Microsoft Entra ID, ITSM platforms,
HRIS, SaaS SSO providers, PAM solutions, and audit/SIEM infrastructure
--- consume this canonical representation through defined event
contracts and sync protocols.

The scope of this blueprint covers the following major functional areas:

- **AD Object Ingestion** --- Users, Groups, Organizational Units,
  Computers, Service Accounts, and Contacts, ingested via LDAP/S polling
  and USN change tracking

- **Normalization and Canonical Schema Mapping** --- Attribute
  sanitization, type casting, and mapping to OrgTree canonical fields

- **OrgTree Node Construction and Hierarchy Assembly** --- Parent-child
  graph construction backed by an adjacency list and closure table

- **OrgPath String Derivation and Lineage Encoding** --- Deterministic,
  normalized lineage strings computed from OrgTree graph traversal

- **Attribute Inheritance Propagation** --- Top-down cascading of
  organizational metadata from parent OrgUnits to child nodes and leaf
  members

- **Lifecycle State Machine** --- Governed transitions across
  Provisioned, Active, Suspended, Deprovisioned, and Archived states,
  driven by AD condition predicates

- **Drift Detection Engine** --- Scheduled and event-driven comparison
  of OrgTree canonical state against live AD, with automated and
  approval-gated remediation

- **Downstream Readiness** --- Defined sync contracts for Microsoft
  Entra ID, ITSM, HRIS, SaaS SSO, PAM, Audit/SIEM, and Data Catalog
  consumers

+----------------------------------------------------------------------+
| **⚠ Implementation Notice**                                          |
|                                                                      |
| All implementation teams must read Sections 3 through 5 before       |
| beginning schema registration. Pre-flight checklist (                |
|                                                                      |
| §                                                                    |
|                                                                      |
| 11.1) must be signed off by AD Operations, IAM Engineering, and SRE  |
| before Phase 2 ingestion begins.                                     |
+----------------------------------------------------------------------+

## 2. Integration Architecture Overview

### 2.1 Component Map

The integration architecture is organized into eight logical layers,
each with a distinct responsibility boundary. Data flows strictly
top-to-bottom through the layers under normal operation; remediation and
lifecycle events may trigger upstream re-reads.

  ---------------------------------------------------------------------------------
  **Layer**   **Name**        **Components**       **Responsibility**
  ----------- --------------- -------------------- --------------------------------
  **Layer 0** AD Source       Domain Controllers   Authoritative source of all
                              (LDAP/S), AD DS      identity and organizational
                              forest, OU tree,     data. Emits USN changes on every
                              schema extensions    object mutation.

  **Layer 1** Ingestion       Provisioning Agent   Detects AD changes via DirSync
              Adapter         (outbound LDAP       cookie or USNChanged polling.
                              polling + USN change Pulls raw LDAP attribute
                              tracking), SCIM      payloads for delta objects.
                              bridge

  **Layer 2** Normalization   Attribute sanitizer, Applies sanitization,
              Engine          canonical type       type-casting, Unicode
                              resolver, delta      normalization, and canonical
                              computation module   attribute mapping. Produces
                                                   normalized change records.

  **Layer 3** OrgTree Builder Node assembly        Constructs or updates OrgNode
                              engine, parent       records. Resolves parent DN to
                              resolver, hierarchy  OrgNode ID. Maintains closure
                              graph manager,       table for O(1) ancestor queries.
                              closure table writer

  **Layer 4** OrgPath         Lineage string       Computes OrgPath from closure
              Derivator       computer, path       table traversal. Caches paths.
                              cache, invalidation  Handles bulk invalidation for
                              trigger handler      subtree renames and moves.

  **Layer 5** State Manager   Lifecycle finite     Evaluates lifecycle predicates
                              state machine (FSM), against OrgNode state. Fires
                              transition logger,   transitions and emits lifecycle
                              event emitter        events to downstream consumers.

  **Layer 6** Drift Detector  Fast cycle engine    Compares canonical OrgTree state
                              (120s), deep         against live AD. Classifies
                              reconciliation       drift, triggers auto-remediation
                              engine (4h), drift   where permitted, raises alerts
                              alert publisher      for manual review.

  **Layer 7** Downstream      SCIM publisher       Fans out normalized change
              Publisher       (Entra ID), webhook  events and lifecycle
                              fanout, Kafka/Event  notifications to all registered
                              Hub streamer, ITSM   downstream consumer endpoints.
                              connector
  ---------------------------------------------------------------------------------

### 2.2 Data Flow Summary

The following sequence describes the end-to-end data flow for a single
AD object change event under steady-state operation:

1.  **Change Emission:** AD DS emits a USN (Update Sequence Number)
    increment on any object create, modify, move, or delete within the
    in-scope OU subtree.

2.  **Delta Detection:** The Ingestion Adapter detects the delta via
    DirSync cookie or USNChanged attribute polling, executing every 120
    seconds per domain.

3.  **Raw Attribute Pull:** Full LDAP attribute set is fetched for each
    changed object using the tracked objectGUID as the stable anchor
    key.

4.  **Normalization:** The Normalization Engine applies attribute
    sanitization, type-casting (e.g., FILETIME→ISO 8601, bitmask→flag
    set), Unicode NFC normalization, and maps each raw LDAP attribute to
    its canonical OrgTree field.

5.  **OrgTree Update:** The OrgTree Builder evaluates the object\'s
    parent DN, resolves the parent OrgNode ID via the closure table,
    then inserts (new) or updates (existing) the OrgNode record with
    optimistic concurrency version bump.

6.  **OrgPath Recomputation:** The OrgPath Derivator recomputes the
    lineage string for the changed node and --- if the node is an
    OrgUnit --- propagates recomputation to all descendants via the
    closure table.

7.  **Lifecycle Evaluation:** The State Manager evaluates lifecycle
    predicates (enabled/disabled status, expiry, OU placement) and fires
    any required state transitions with reason codes and timestamps.

8.  **Drift Baseline Update:** The Drift Detector records a canonical
    snapshot for the updated node and resets its next comparison
    schedule.

9.  **Downstream Fan-out:** The Downstream Publisher emits
    CloudEvents-structured change notifications to all registered
    consumer endpoints, with per-consumer field filtering applied.

+----------------------------------------------------------------------+
| **ℹ Note on Processing Order**                                       |
|                                                                      |
| During initial ingestion and after deep reconciliation cycles,       |
| OrgUnit objects are always processed before leaf objects (users,     |
| groups, computers) to ensure parent OrgNode IDs exist before child   |
| nodes reference them. See                                            |
|                                                                      |
| §                                                                    |
|                                                                      |
| 11.1, Phase 2 checklist.                                             |
+----------------------------------------------------------------------+

## 3. AD Source Schema --- Canonical Object Taxonomy

### 3.1 Object Classes Ingested

The following AD object classes are within ingestion scope. Processing
is executed in priority order to ensure structural parents are available
before leaf object parent resolution is attempted.

  --------------------------------------------------------------------------------------------
  **AD Object Class**          **OrgTree Node       **Ingestion   **Notes**
                               Type**               Priority**
  ---------------------------- -------------------- ------------- ----------------------------
  organizationalUnit           OrgUnit              1 --- Highest Forms the structural
                                                                  skeleton of the OrgTree.
                                                                  Must be fully processed
                                                                  before any leaf object
                                                                  ingestion begins.

  user                         OrgMember            2             Standard employee or
                                                                  identity account. Requires
                                                                  OU parent resolution for
                                                                  OrgPath derivation.

  group                        OrgGroup             3             Security and distribution
                                                                  groups. Membership graph is
                                                                  flattened to both direct and
                                                                  transitive closure sets.

  computer                     OrgDevice            4             Workstations and servers.
                                                                  Linked to OrgMember records
                                                                  via the managedBy attribute.

  msDS-ManagedServiceAccount / OrgServiceIdentity   5             Non-human service
  gMSA                                                            identities.
                                                                  Lifecycle-managed separately
                                                                  from human OrgMembers.
                                                                  Flagged for PAM monitoring.

  contact                      OrgContact           6             External identities.
                                                                  Ingested as read-only nodes
                                                                  in OrgTree. Not eligible for
                                                                  downstream provisioning.

  inetOrgPerson                OrgMember            2             Treated as equivalent to
                                                                  user. Distinguished by flag:
                                                                  inetOrgPerson=true in
                                                                  OrgNode record.
  --------------------------------------------------------------------------------------------

### 3.2 Core AD Attributes --- User Object

The table below defines every tracked LDAP attribute for user objects,
its normalization rule, and its mapping to the OrgTree canonical field.
Required attributes must be present for OrgNode provisioning to succeed;
missing required attributes cause the object to be quarantined pending
remediation.

  ------------------------------------------------------------------------------------------------------------------------------------------------
  **AD Attribute**             **LDAP OID Alias**           **Data Type**     **Required**   **Normalization Rule**         **Maps To (OrgTree
                                                                                                                            Field)**
  ---------------------------- ---------------------------- ----------------- -------------- ------------------------------ ----------------------
  objectGUID                   objectGUID                   UUID              **Yes**        Binary→UUID v4 string format   orgNodeId (immutable
                                                                                             (8-4-4-4-12 hyphenated hex)    anchor)

  distinguishedName            DN                           String            **Yes**        Parse OU path segments; strip  orgPathRaw
                                                                                             DC= components for raw path    (pre-normalization)
                                                                                             construction

  sAMAccountName               sAMAccountName               String            **Yes**        Lowercase; strip domain prefix loginName
                                                                                             if present (e.g., CORP\\jsmith
                                                                                             → jsmith)

  userPrincipalName            UPN                          String            **Yes**        Validate RFC 5322 format;      upn / emailHint
                                                                                             extract domain suffix for
                                                                                             routing

  displayName                  displayName                  String            **Yes**        Trim leading/trailing          displayName
                                                                                             whitespace; normalize to
                                                                                             Unicode NFC

  givenName                    givenName                    String            No             Trim whitespace                firstName

  sn (surname)                 sn                           String            No             Trim whitespace                lastName

  department                   department                   String            No             Map via                        department (canonical)
                                                                                             DepartmentNormalizationTable
                                                                                             to HRIS canonical name

  title                        title                        String            No             Trim; map to JobTitleCatalog   jobTitle
                                                                                             entry if available; pass
                                                                                             through if no match

  manager                      manager                      DN                No             Resolve DN → objectGUID; set   managerRef (OrgNode
                                                                                             as managerOrgNodeId reference  pointer)

  memberOf                     memberOf                     DN\[\]            No             Resolve each DN → Group        groupMemberships\[\]
                                                                                             OrgNode ID; flatten nested via
                                                                                             BFS transitive closure

  mail                         mail                         String            No             Validate RFC 5322 format;      primaryEmail
                                                                                             convert to lowercase

  telephoneNumber              telephoneNumber              String            No             Normalize to E.164             phoneNumber
                                                                                             international format (e.g.,
                                                                                             +12025551234)

  physicalDeliveryOfficeName   physicalDeliveryOfficeName   String            No             Map to OfficeCatalog canonical officeLocation
                                                                                             entry; pass through raw value
                                                                                             if no match

  employeeID                   employeeID                   String            No             Strip leading zeros;           employeeId (HRIS
                                                                                             cross-reference HRIS for       anchor)
                                                                                             validation

  employeeType                 employeeType                 String            No             Map to enum: Employee /        memberType (enum)
                                                                                             Contractor / Vendor / Guest

  accountExpires               accountExpires               FILETIME          No             Convert: FILETIME → ISO 8601   expiresAt (nullable)
                                                                                             UTC; value 0 or
                                                                                             9223372036854775807 = never
                                                                                             expires (set null)

  userAccountControl           userAccountControl           Integer (bitmask) **Yes**        Parse individual flags:        accountStatus flags
                                                                                             ACCOUNTDISABLE (0x2), LOCKOUT  object
                                                                                             (0x10), NORMAL_ACCOUNT
                                                                                             (0x200), DONT_EXPIRE_PASSWORD
                                                                                             (0x10000), etc.

  whenCreated                  whenCreated                  GeneralizedTime   **Yes**        Parse GeneralizedTime → ISO    createdAt
                                                                                             8601 UTC

  whenChanged                  whenChanged                  GeneralizedTime   **Yes**        Parse GeneralizedTime → ISO    lastModifiedAt
                                                                                             8601 UTC

  pwdLastSet                   pwdLastSet                   FILETIME          No             Convert FILETIME → ISO 8601;   passwordLastSetAt
                                                                                             value 0 = password must be
                                                                                             changed at next logon

  lastLogonTimestamp           lastLogonTimestamp           FILETIME          No             Convert FILETIME → ISO 8601;   lastActivityAt
                                                                                             note: replication lag up to 14
                                                                                             days; use as approximate
                                                                                             activity indicator only

  uSNChanged                   uSNChanged                   Integer           **Yes**        Track per-DC high-watermark    internalUSN
                                                                                             for delta detection; store
                                                                                             alongside DC FQDN

  objectSid                    objectSid                    SID (binary)      **Yes**        Binary → string format         sid (secondary lookup
                                                                                             S-1-5-21-\... using standard   key)
                                                                                             SID conversion

  extensionAttribute1--15      extensionAttribute1--15      String            No             Pass through; map via          customAttributes{} map
                                                                                             ExtensionAttributeConfig YAML
                                                                                             to semantic field names
  ------------------------------------------------------------------------------------------------------------------------------------------------

### 3.3 Core AD Attributes --- OU Object

  -------------------------------------------------------------------------------
  **AD Attribute**         **Data Type**     **Maps To (OrgTree Field)**
  ------------------------ ----------------- ------------------------------------
  objectGUID               UUID              orgNodeId

  distinguishedName        String            orgPathRaw

  name                     String            ouName / displayName

  description              String            description

  ou                       String            shortName (preferred segment value
                                             for OrgPath derivation)

  gPLink                   String\[\]        policyLinks\[\] (parsed GPO GUID
                                             list for GPO inheritance tracking)

  managedBy                DN                ouAdminRef (resolved to orgNodeId of
                                             delegated admin)

  whenCreated              GeneralizedTime   createdAt

  whenChanged              GeneralizedTime   lastModifiedAt

  uSNChanged               Integer           internalUSN

  isCriticalSystemObject   Boolean           isSystemOU --- system OUs are
                                             skipped from OrgTree processing
                                             unless explicitly whitelisted in
                                             configuration
  -------------------------------------------------------------------------------

### 3.4 Core AD Attributes --- Group Object

  ------------------------------------------------------------------------------
  **AD Attribute**    **Data Type**     **Maps To (OrgTree Field)**
  ------------------- ----------------- ----------------------------------------
  objectGUID          UUID              orgNodeId

  distinguishedName   String            orgPathRaw

  cn                  String            groupName

  description         String            description

  groupType           Integer (bitmask) groupScope (DomainLocal / Global /
                                        Universal) + groupCategory (Security /
                                        Distribution). See §9.1 for bitmask
                                        decoding.

  member              DN\[\]            memberRefs\[\] (resolved to
                                        orgNodeId\[\])

  memberOf            DN\[\]            parentGroupRefs\[\] (resolved to
                                        orgNodeId\[\])

  managedBy           DN                groupOwnerRef (resolved to orgNodeId)

  mail                String            groupEmail (nullable; present for
                                        mail-enabled groups)

  whenCreated         GeneralizedTime   createdAt

  whenChanged         GeneralizedTime   lastModifiedAt
  ------------------------------------------------------------------------------

## 4. OrgTree Schema Definition

### 4.1 OrgNode --- Canonical Record

The OrgNode is the atomic unit of the OrgTree. Every ingested AD object
--- regardless of class --- is represented as a single OrgNode record
conforming to the following JSON Schema (Draft 2020-12). The schema is
versioned and published at the internal schema registry endpoint.

{ \"\$schema\": \"https://orgschema.internal/orgtree/orgnode/v1\",
\"type\": \"object\", \"required\": \[ \"orgNodeId\", \"nodeType\",
\"displayName\", \"orgPath\", \"lifecycleState\", \"sourceAnchor\" \],
\"properties\": { \"orgNodeId\": { \"type\": \"string\", \"format\":
\"uuid\", \"description\": \"Immutable. Derived from AD objectGUID.
Never reused after archival.\" }, \"nodeType\": { \"type\": \"string\",
\"enum\": \[\"OrgUnit\",\"OrgMember\",\"OrgGroup\",\"OrgDevice\",
\"OrgServiceIdentity\",\"OrgContact\"\] }, \"displayName\": { \"type\":
\"string\" }, \"shortName\": { \"type\": \"string\", \"description\":
\"OU short name (ou attr) or sAMAccountName for users.\" }, \"orgPath\":
{ \"type\": \"string\", \"description\": \"Computed lineage string. See
OrgPath specification §5.\" }, \"orgPathSegments\": { \"type\":
\"array\", \"items\": { \"type\": \"string\" }, \"description\":
\"Ordered segment array from domain root to self.\" }, \"depth\": {
\"type\": \"integer\", \"minimum\": 0, \"description\": \"Tree depth. 0
= domain root OU.\" }, \"parentOrgNodeId\": { \"type\":
\[\"string\",\"null\"\], \"format\": \"uuid\" }, \"ancestorIds\": {
\"type\": \"array\", \"items\": { \"type\": \"string\", \"format\":
\"uuid\" }, \"description\": \"Ordered list of ancestor orgNodeIds from
root to direct parent.\" }, \"lifecycleState\": { \"type\": \"string\",
\"enum\":
\[\"Provisioned\",\"Active\",\"Suspended\",\"Deprovisioned\",\"Archived\"\]
}, \"lifecycleReason\": { \"type\": \[\"string\",\"null\"\],
\"description\": \"Human-readable description of the last lifecycle
trigger.\" }, \"lifecycleAt\": { \"type\": \"string\", \"format\":
\"date-time\" }, \"sourceAnchor\": { \"type\": \"string\",
\"description\": \"AD objectGUID in UUID format. Immutable identity
anchor.\" }, \"sourceDN\": { \"type\": \"string\", \"description\":
\"Last known AD distinguishedName. Informational only.\" },
\"sourceDomain\": { \"type\": \"string\", \"description\": \"FQDN of
originating AD domain (e.g., corp.internal).\" }, \"sid\": { \"type\":
\"string\", \"description\": \"AD SID string in S-1-5-21-\... format.\"
}, \"upn\": { \"type\": \[\"string\",\"null\"\] }, \"loginName\": {
\"type\": \[\"string\",\"null\"\] }, \"primaryEmail\": { \"type\":
\[\"string\",\"null\"\] }, \"employeeId\": { \"type\":
\[\"string\",\"null\"\] }, \"memberType\": { \"type\":
\[\"string\",\"null\"\], \"enum\":
\[\"Employee\",\"Contractor\",\"Vendor\",\"Guest\",\"Service\",null\] },
\"jobTitle\": { \"type\": \[\"string\",\"null\"\] }, \"department\": {
\"type\": \[\"string\",\"null\"\] }, \"officeLocation\": { \"type\":
\[\"string\",\"null\"\] }, \"managerRef\": { \"type\":
\[\"string\",\"null\"\], \"format\": \"uuid\", \"description\":
\"orgNodeId of reporting manager.\" }, \"groupMemberships\": { \"type\":
\"array\", \"items\": { \"type\": \"string\", \"format\": \"uuid\" },
\"description\": \"Direct group memberships (orgNodeId of each group).\"
}, \"effectiveGroupMemberships\": { \"type\": \"array\", \"items\": {
\"type\": \"string\", \"format\": \"uuid\" }, \"description\":
\"Transitive (flattened) group memberships. See §9.2.\" },
\"inheritedAttributes\": { \"type\": \"object\", \"description\":
\"Attributes propagated from ancestor OrgUnits. See §6.\" },
\"customAttributes\": { \"type\": \"object\", \"description\":
\"extensionAttribute1-15 passthrough map, keyed by semantic name.\" },
\"accountStatus\": { \"type\": \"object\", \"properties\": {
\"isEnabled\": { \"type\": \"boolean\" }, \"isLocked\": { \"type\":
\"boolean\" }, \"isExpired\": { \"type\": \"boolean\" }, \"expiresAt\":
{ \"type\": \[\"string\",\"null\"\], \"format\": \"date-time\" } } },
\"policyLinks\": { \"type\": \"array\", \"items\": { \"type\":
\"string\" }, \"description\": \"GPO GUIDs linked to this OU or
inherited from ancestors.\" }, \"createdAt\": { \"type\": \"string\",
\"format\": \"date-time\" }, \"lastModifiedAt\": { \"type\": \"string\",
\"format\": \"date-time\" }, \"lastSyncedAt\": { \"type\": \"string\",
\"format\": \"date-time\" }, \"lastDriftCheckedAt\": { \"type\":
\[\"string\",\"null\"\], \"format\": \"date-time\" }, \"driftFlags\": {
\"type\": \"array\", \"items\": { \"type\": \"string\" },
\"description\": \"Active drift condition codes for this node.\" },
\"version\": { \"type\": \"integer\", \"description\": \"Monotonic write
version for optimistic concurrency control.\" } } }

### 4.2 OrgTree Graph Model

The OrgTree is stored as a **directed acyclic graph (DAG)** with the
following structural invariants enforced at write time:

- Every node has exactly one parent, except the domain root node which
  is parentless (parentOrgNodeId = null)

- A node\'s depth is always parent.depth + 1; the domain root has depth
  = 0

- Cycles are structurally impossible given AD OU tree rules, but cycle
  detection is applied during ingestion as a defensive guard against
  data corruption

- The graph is materialized in two complementary representations:

  1.  **Adjacency list** --- stored in the OrgNode record
      (parentOrgNodeId, ancestorIds\[\]) for efficient parent-child
      traversal

      **Closure table** --- rows of (ancestorId, descendantId,
      depth_delta) enabling O(1) ancestor/descendant queries and
      efficient subtree operations via a single SQL JOIN

- Maximum supported tree depth is configurable (default: 10 levels);
  objects beyond this depth are quarantined and flagged for OU
  restructuring review

### 4.3 Closure Table Schema

The closure table is the primary enabler of efficient subtree queries,
ancestor lookups, and OrgPath bulk recomputation. Every node has a
self-referential row (depth_delta = 0). New nodes are inserted with rows
for every ancestor plus themselves.

\-- ============================================================ \--
OrgTree Closure Table DDL \-- Supports: ancestor queries, subtree
queries, depth queries \--
============================================================ CREATE
TABLE orgtree_closure ( ancestor_id UUID NOT NULL REFERENCES
orgnode(org_node_id) ON DELETE CASCADE, descendant_id UUID NOT NULL
REFERENCES orgnode(org_node_id) ON DELETE CASCADE, depth_delta INTEGER
NOT NULL CHECK (depth_delta \>= 0), PRIMARY KEY (ancestor_id,
descendant_id) ); \-- Self-referential row inserted for every new node
on creation: \-- INSERT INTO orgtree_closure VALUES (node_id, node_id,
0); \-- Insert ancestry rows when adding a new node with parent_id: \--
INSERT INTO orgtree_closure (ancestor_id, descendant_id, depth_delta)
\-- SELECT ancestor_id, :new_node_id, depth_delta + 1 \-- FROM
orgtree_closure \-- WHERE descendant_id = :parent_id \-- UNION ALL \--
SELECT :new_node_id, :new_node_id, 0; CREATE INDEX
idx_closure_descendant ON orgtree_closure(descendant_id); CREATE INDEX
idx_closure_ancestor ON orgtree_closure(ancestor_id); CREATE INDEX
idx_closure_depth ON orgtree_closure(depth_delta); \-- Subtree query
example (get all descendants of a node): \-- SELECT descendant_id FROM
orgtree_closure \-- WHERE ancestor_id = :target_node_id AND depth_delta
\> 0; \-- Ancestor chain query (ordered root-to-parent): \-- SELECT
ancestor_id, depth_delta FROM orgtree_closure \-- WHERE descendant_id =
:target_node_id AND depth_delta \> 0 \-- ORDER BY depth_delta DESC;

## 5. OrgPath Specification

### 5.1 OrgPath Format

OrgPath is a **human-readable, machine-parseable lineage string**
encoding the full ancestry chain of an OrgNode from the domain root to
the node itself. It is derived deterministically from the OrgTree graph
--- **not** directly from the AD distinguishedName. This decoupling
ensures OrgPaths remain stable and canonical even when AD DN formatting
conventions change.

**Format template:**

/{domainShortName}/{L1_ouName}/{L2_ouName}/\.../{nodeShortName}

**Construction rules:**

10. Segments are separated by the forward slash character /

11. A leading slash is mandatory; a trailing slash is forbidden

12. Segment characters are normalized: lowercase, spaces converted to
    underscores, all characters except \[a-z0-9\_-\] are stripped

13. The domain root segment equals the NETBIOS name of the AD domain,
    lowercased (e.g., CORP → corp)

14. OU segments use the normalized ou attribute value; if blank, fall
    back to the normalized name attribute

15. Leaf segment for OrgMember = loginName (sAMAccountName); for
    OrgGroup = normalized cn

16. System OUs (isCriticalSystemObject=true) that are whitelisted appear
    as \_sys\_{ouName}

17. Maximum total path length: 2,048 characters; individual segments are
    truncated at 64 characters

**Example OrgPaths:**

/corp/employees/engineering/backend/jsmith
/corp/contractors/acme_corp/bdavis /corp/groups/security/vpn_users
/corp/service_accounts/app_layer/svc_payroll
/corp/computers/workstations/nyc_office/ws0142
/corp/\_sys_builtin/domain_admins

### 5.2 OrgPath Derivation Algorithm

OrgPath is derived by traversing the closure table to retrieve the
ordered ancestor chain, then normalizing each segment. The algorithm is
deterministic for a given OrgTree state.

function deriveOrgPath(orgNodeId): \-- Query closure table for all
ancestors, ordered from root (highest depth_delta) to self ancestors \<-
queryClosureTable( descendant = orgNodeId, ORDER BY depth_delta DESC \--
depth_delta DESC = root first ) \-- ancestors\[0\] = domain root node
\-- ancestors\[-1\] = self segments \<- \[\] for each node in ancestors:
raw \<- node.shortName ?? node.displayName \-- prefer shortName (ou attr
/ sAMAccountName) segment \<- normalizeSegment(raw)
segments.append(segment) orgPath \<- \"/\" + join(segments, \"/\")
return orgPath function normalizeSegment(raw): s \<-
toLower(unicodeNFC(raw)) \-- lowercase + Unicode NFC normalization s \<-
replaceAll(s, \" \", \"\_\") \-- spaces to underscores s \<-
removeChars(s, \"\[\^a-z0-9\_\\-\]\") \-- strip non-alphanumeric except
\_ and - s \<- truncate(s, maxLen = 64) \-- enforce segment length limit
if len(s) == 0: s \<- \"\_unknown\_\" \-- safety fallback for empty
segments return s

### 5.3 OrgPath Cache Invalidation

OrgPaths are cached in the OrgNode record and must be explicitly
invalidated and recomputed whenever a structural change occurs. The
following table defines the complete set of invalidation triggers and
their scope:

  ------------------------------------------------------------------------
  **Trigger Event**   **Scope of       **Action**
                      Invalidation**
  ------------------- ---------------- -----------------------------------
  OU renamed (ou or   Self + all       Bulk recompute OrgPath for entire
  name attribute      descendants      subtree via closure table; write
  changed)                             orgpath_history row for each
                                       affected node; emit PathChanged
                                       event

  OU moved (DN change Self + all       Update parent reference + rebuild
  / re-parent in AD)  descendants      closure table rows for subtree;
                                       recompute all OrgPaths in subtree;
                                       notify downstream consumers

  User or object      Self only        Recompute single OrgPath; update
  moved to new OU                      closure table rows for this node
                                       only; emit PathChanged event

  Parent OU deleted   Self + all       Transition all children to
                      descendants      Deprovisioned lifecycle state; mark
                                       OrgPaths stale; hold until
                                       re-parented or archived

  Domain rename       Entire domain    Full OrgPath recomputation job for
                      tree             all nodes in domain; requires
                                       maintenance window; treat as
                                       schema-level migration event

  Normalization rule  All nodes        Batch recomputation job; schema
  change (segment     matching the     version bump; coordinate with
  character rules     changed          downstream consumers before
  updated)            normalization    activation
                      rule
  ------------------------------------------------------------------------

### 5.4 OrgPath Versioning

Every OrgPath change is recorded in an append-only orgpath_history
ledger table. This enables downstream consumers to detect path renames
and reliably update stale references, and supports audit trail
requirements for organizational restructuring events.

\-- ============================================================ \--
OrgPath History Ledger DDL \-- Append-only; never update or delete rows
\-- ============================================================ CREATE
TABLE orgpath_history ( id BIGSERIAL PRIMARY KEY, org_node_id UUID NOT
NULL, old_path TEXT, \-- NULL on first-time path assignment new_path
TEXT NOT NULL, change_reason TEXT, \-- e.g. \"OU renamed\", \"Node
moved\", \"drift_correction\" changed_at TIMESTAMPTZ NOT NULL DEFAULT
now(), changed_by TEXT NOT NULL \-- service identity or
\"ad_sync_agent\" ); CREATE INDEX idx_orgpath_history_node ON
orgpath_history(org_node_id, changed_at DESC); CREATE INDEX
idx_orgpath_history_time ON orgpath_history(changed_at DESC);

## 6. Attribute Inheritance Propagation

### 6.1 Inheritance Model

OrgTree implements a **top-down cascading inheritance** model for
organizational metadata attributes. Attributes set on a parent OrgUnit
flow down to all child OrgUnits and their leaf OrgMember nodes. This is
conceptually analogous to Active Directory Group Policy inheritance but
operates on organizational metadata rather than policy objects.

Key behavioral rules of the inheritance model:

- Inherited attributes are stored in the inheritedAttributes object
  within each OrgNode, clearly distinguished from directly-set
  attributes in the node\'s own property fields

- A child node can **override** an inherited attribute if the
  attribute\'s overrideAllowed flag is true, by explicitly setting that
  attribute on its own record

- Some attributes (e.g., environmentTier, ouAdminRef) are
  **non-overridable** --- the root-set or nearest-ancestor value always
  flows down unchanged regardless of any child value

- Additive attributes (e.g., complianceTags) accumulate the union of all
  ancestor values plus any child-added values

- Restrictive attributes (e.g., dataClassification) allow children to
  only increase the restriction level, never decrease it

- Inheritance is recomputed for all affected descendants whenever a
  parent node\'s inheritable attribute changes

### 6.2 Inheritable Attribute Catalog

  -----------------------------------------------------------------------------------------------------------------------
  **Attribute Key**    **Inheritable?**   **Override     **Merge Strategy**           **Description**
                                          Allowed?**
  -------------------- ------------------ -------------- ---------------------------- -----------------------------------
  costCenter           Yes                Yes (leaf      Last-write-wins; child value Finance cost allocation code for
                                          override)      takes precedence             chargebacks and reporting

  businessUnit         Yes                Yes            Child wins                   Top-level business unit name (e.g.,
                                                                                      \"Corporate IT\", \"Sales\")

  region               Yes                Yes            Child wins                   Geographic region identifier: AMER,
                                                                                      EMEA, APAC, or sub-region

  complianceTags       Yes                Yes (additive) Union of all ancestor sets + Regulatory compliance tags, e.g.,
                                                         child set                    \[\"SOX\",\"HIPAA\",\"PCI-DSS\"\]

  dataClassification   Yes                Yes            Child may only increase      Ordered scale: PUBLIC \< INTERNAL
                                          (restrictive   restriction level; cannot    \< CONFIDENTIAL \< RESTRICTED
                                          only)          reduce below inherited value

  policyLinks (GPO)    Yes                No (blocked by Accumulate from ancestors    GPO GUIDs from gPLink; mirrors AD
                                          AD Block       unless GPO Block Inheritance GPO inheritance behavior
                                          Inheritance    is set at this OU
                                          flag)

  officeLocation       Yes                Yes            Child wins; user\'s          Physical office location; inherited
                                                         physicalDeliveryOfficeName   from OU, overridable at user level
                                                         takes final precedence

  ouAdminRef           Yes                No             Nearest ancestor\'s value    Delegated administrative contact
                                                         (closest OU with managedBy   for the OU subtree
                                                         set)

  retentionPolicy      Yes                Yes            Child wins                   Data retention class identifier;
                                                                                      maps to retention policy engine
                                                                                      rules

  environmentTier      Yes                No             Root-set; flows down         Deployment environment: PROD,
                                                         unchanged to all descendants NON-PROD, or STAGING
  -----------------------------------------------------------------------------------------------------------------------

### 6.3 Inheritance Resolution Algorithm

function resolveInheritedAttributes(orgNodeId): \-- Retrieve full
ancestor chain ordered from domain root to direct parent ancestors \<-
queryClosureTable( descendant = orgNodeId, depth_delta \> 0, ORDER BY
depth_delta DESC \-- root first, direct parent last ) accumulated \<- {}
\-- working accumulator for inherited values \-- Pass 1: walk ancestors
root→parent, applying merge strategy at each level for each ancestor in
ancestors: \-- root to direct parent for each attr in
inheritableAttributes: if ancestor.directAttributes\[attr\] is not null:
mergeStrategy \<- getMergeStrategy(attr) \-- from attribute catalog if
mergeStrategy == \"child_wins\": accumulated\[attr\] \<-
ancestor.directAttributes\[attr\] \-- later ancestor wins else if
mergeStrategy == \"union\": accumulated\[attr\] \<-
union(accumulated\[attr\], ancestor.directAttributes\[attr\]) else if
mergeStrategy == \"restrictive_only\": if
restrictionLevel(ancestor.directAttributes\[attr\]) \>
restrictionLevel(accumulated\[attr\]): accumulated\[attr\] \<-
ancestor.directAttributes\[attr\] \-- only increase restriction else if
mergeStrategy == \"nearest_ancestor\": if accumulated\[attr\] is null:
accumulated\[attr\] \<- ancestor.directAttributes\[attr\] \-- first
(root) match wins \-- Pass 2: apply child\'s own direct attributes where
override is permitted selfNode \<- getOrgNode(orgNodeId) for each attr
in inheritableAttributes: if selfNode.directAttributes\[attr\] is not
null: if attr.overrideAllowed: if attr.mergeStrategy == \"union\":
accumulated\[attr\] \<- union(accumulated\[attr\],
selfNode.directAttributes\[attr\]) else if attr.mergeStrategy ==
\"restrictive_only\": if
restrictionLevel(selfNode.directAttributes\[attr\]) \>
restrictionLevel(accumulated\[attr\]): accumulated\[attr\] \<-
selfNode.directAttributes\[attr\] else: accumulated\[attr\] \<-
selfNode.directAttributes\[attr\] \-- override \-- else:
overrideAllowed=false; silently ignore child value; ancestor value
persists selfNode.inheritedAttributes \<- accumulated return accumulated

## 7. Lifecycle State Machine

### 7.1 States

  ----------------------------------------------------------------------------------
  **State**           **Description**      **AD Condition        **Sync Behavior**
                                           Predicates**
  ------------------- -------------------- --------------------- -------------------
  **Provisioned**     Object has been      objectGUID exists;    Synced to OrgTree;
                      created in AD and    userAccountControl    **excluded from
                      ingested into        may include           downstream
                      OrgTree, but has not ACCOUNTDISABLE; no    consumers** until
                      yet been validated   lastLogonTimestamp    transition to
                      or activated.        recorded              Active
                      Pending first-use
                      confirmation.

  **Active**          Account is in full   ACCOUNTDISABLE bit =  Fully synced to all
                      normal operational   0; accountExpires is  downstream
                      state. Identity is   null or in the        consumers with no
                      valid and accessible future; account not   restrictions
                      to all registered    locked
                      downstream
                      consumers.

  **Suspended**       Account is           ACCOUNTDISABLE = 1,   Synced; downstream
                      temporarily          OR accountExpires is  consumers receive
                      disabled. Identity   past but within grace suspended=true;
                      record is preserved  window (default: 90   access tokens
                      in full. Access is   days from expiry)     revoked; account
                      revoked across all                         preserved for
                      downstream systems.                        reactivation

  **Deprovisioned**   Account has been     Object moved to       OrgNode retained in
                      formally removed or  designated Disabled   read-only state;
                      disabled beyond the  OU (matching          orgPath suffixed
                      grace window.        DisabledOUPattern),   with
                      Identity data        OR AD tombstone       /\_deprovisioned;
                      retained with        detected, OR AD       all downstream
                      sensitive attributes delete event received consumers notified
                      stripped.                                  of deprovisioning

  **Archived**        Permanent            AD tombstone          OrgNode is
                      end-of-life state.   retention period      read-only; removed
                      Identity data        elapsed, OR explicit  from active OrgTree
                      retained for audit   archival trigger      index; queryable
                      and legal hold       fired by IAM admin    exclusively via
                      purposes only. No                          archive index; no
                      operational use                            downstream sync
                      permitted.
  ----------------------------------------------------------------------------------

### 7.2 Lifecycle Transition Rules

  -------------------------------------------------------------------------------------------------
  **From State**  **To State**        **Trigger**    **Guard Conditions**    **Actions Fired**
  --------------- ------------------- -------------- ----------------------- ----------------------
  Provisioned     **Active**          Account first  UAC ACCOUNTDISABLE bit  Emit ActivationEvent;
                                      enabled in AD  = 0 AND                 begin downstream sync;
                                                     lastLogonTimestamp      set lifecycleAt =
                                                     recorded                now()

  Active          **Suspended**       Account        UAC ACCOUNTDISABLE = 1  Emit SuspensionEvent;
                                      disabled or    OR accountExpires \<    revoke downstream
                                      account expiry now()                   access tokens; set
                                      reached                                lifecycleReason;
                                                                             notify PAM

  Suspended       **Active**          Account        UAC ACCOUNTDISABLE = 0  Emit
                                      re-enabled in  AND accountExpires \>   ReactivationEvent;
                                      AD             now() (or null)         restore downstream
                                                                             access; clear
                                                                             lifecycleReason

  Active          **Deprovisioned**   Object moved   DN matches              Emit
                                      to Disabled OU DisabledOUPattern OR AD DeprovisioningEvent;
                                      or deleted     tombstone/delete event  strip sensitive
                                      from AD        detected                attributes; append
                                                                             /\_deprovisioned to
                                                                             OrgPath; notify all
                                                                             consumers

  Suspended       **Deprovisioned**   Grace window   now() - suspendedAt \>  Same as Active →
                                      elapsed        graceWindowDays         Deprovisioned above
                                      without        (default: 90 days)
                                      reactivation

  Deprovisioned   **Archived**        Retention      now() - deprovisionedAt Emit ArchivalEvent;
                                      period elapsed \> retentionDays        move OrgNode to
                                                     (default: 365 days)     archive store; purge
                                                                             from active OrgTree
                                                                             index

  Any             **Provisioned**     Object         AD                      Emit RestorationEvent;
                                      restored from  restoreFromRecycleBin   revalidate all
                                      AD Recycle Bin event detected;         attributes; re-derive
                                                     objectGUID matches      OrgPath; reassign
                                                     existing Archived or    lifecycle state based
                                                     Deprovisioned OrgNode   on restored account
                                                                             state
  -------------------------------------------------------------------------------------------------

### 7.3 Lifecycle Event Payload Schema

All lifecycle transition events are emitted to downstream consumers and
the audit/SIEM stream using the following payload structure:

{ \"eventId\": \"3f8a1b2c-4d5e-6f7a-8b9c-0d1e2f3a4b5c\", \"eventType\":
\"OrgNode.LifecycleTransition\", \"orgNodeId\":
\"a1b2c3d4-e5f6-7a8b-9c0d-e1f2a3b4c5d6\", \"nodeType\": \"OrgMember\",
\"fromState\": \"Active\", \"toState\": \"Suspended\", \"reason\":
\"ACCOUNTDISABLE flag set in AD (userAccountControl bit 2)\",
\"triggeredBy\": \"ad_sync_agent\", \"occurredAt\":
\"2026-05-07T17:49:00Z\", \"affectedDownstream\": \[\"EntraID\",
\"ITSM\", \"SaaS_SSO\", \"AuditLog\", \"PAM\"\] }

## 8. Drift Detection Engine

### 8.1 Drift Definition

**Drift** is any divergence between the canonical OrgTree/OrgPath state
persisted in the system of record and what Active Directory currently
reports as ground truth. Drift is expected to occur and must be detected
and remediated continuously. Common sources of drift include:

- Direct AD edits performed outside the integration layer (e.g., manual
  AD Users and Computers changes)

- AD replication lag between domain controllers creating temporarily
  inconsistent views

- Sync agent failures, network interruptions, or processing errors
  causing missed change events

- Manual OrgTree overrides applied by administrators for operational
  reasons

- Out-of-band provisioning by external tools or scripts that bypass the
  integration adapter

- Normalization rule or schema changes applied to the OrgTree without
  corresponding re-sync

+----------------------------------------------------------------------+
| **⚠ Critical Drift Category**                                        |
|                                                                      |
| Lifecycle Mismatch drift --- where AD reports an account as disabled |
| but OrgTree still shows Active state --- is classified as Critical   |
| severity and triggers immediate automated remediation without        |
| requiring manual approval. This prevents unauthorized continued      |
| access.                                                              |
+----------------------------------------------------------------------+

### 8.2 Drift Categories

  ------------------------------------------------------------------------------------------------
  **Drift      **Detection Method**   **Severity**   **Auto-Remediate?**   **Remediation Action**
  Category**
  ------------ ---------------------- -------------- --------------------- -----------------------
  Attribute    Compare MD5/SHA-256    **Low**        Yes                   Re-sync single
  Drift        hash of normalized AD                                       attribute to AD current
               attribute value                                             value; log delta in
               against stored OrgNode                                      audit trail
               field value

  Path Drift   Recompute expected     **Medium**     Yes                   Recompute OrgPath;
               OrgPath from current                                        update closure table;
               AD DN; compare against                                      write orgpath_history
               stored orgPath                                              row; notify downstream
                                                                           consumers

  Orphan Node  OrgNode record exists  **High**       No (requires          Flag as orphan; trigger
               with a sourceAnchor                   approval)             SRE review;
               (objectGUID) that is                                        auto-deprovision after
               not found in AD during                                      72h if unresolved
               deep reconciliation                                         (configurable)

  Ghost Object AD object found during **High**       Yes                   Ingest object; create
               deep reconciliation                                         new OrgNode; assign
               with no corresponding                                       Provisioned lifecycle
               OrgNode record                                              state; trigger
                                                                           downstream notification

  Parent       OrgNode                **High**       Yes                   Update parentOrgNodeId;
  Mismatch     parentOrgNodeId does                                        rebuild closure table
               not match the resolved                                      subtree rows; fire
               parent of the                                               PathChanged event to
               object\'s current AD                                        downstream
               DN

  Lifecycle    Computed lifecycle     **Critical**   Yes                   Execute lifecycle FSM
  Mismatch     state from AD                                               transition immediately;
               predicates does not                                         set lifecycleReason =
               match stored OrgNode                                        \"drift_correction\";
               lifecycleState                                              log in audit trail with
                                                                           full before/after diff

  Group        AD memberOf set for an **Medium**     Yes                   Re-sync direct and
  Membership   object differs from                                         effective memberships;
  Drift        stored                                                      notify access-control
               groupMemberships\[\]                                        consumers (SSO, PAM)
               in OrgNode

  Stale        lastSyncedAt exceeds   **Low**        Yes                   Schedule forced
  Timestamp    drift detection                                             full-attribute read for
               interval (default: 10                                       the stale object;
               minutes) with no                                            verify USN counter
               corresponding USN                                           continuity per DC
               change detected
  ------------------------------------------------------------------------------------------------

### 8.3 Drift Detection Cycle

// ============================================================ // FAST
CYCLE --- Runs every 120 seconds per domain // USN-based delta detection
for near-real-time change capture //
============================================================ function
fastDriftCycle(): for each AD domain in scope: cookie \<-
loadDirSyncCookie(domain) // persisted in Redis cache changes \<-
ADDirSync(domain, cookie) // LDAP DirSync control for each
changed_object in changes: processObjectChange(changed_object) //
normalize + upsert OrgNode saveDirSyncCookie(domain, changes.newCookie)
// ============================================================ // DEEP
CYCLE --- Runs every 4 hours // Full reconciliation for orphan/ghost
detection + complete drift audit //
============================================================ function
deepReconciliationCycle(): allADObjects \<- ldapQuery( filter =
\"(\|(objectClass=user)(objectClass=organizationalUnit)\" +
\"(objectClass=group)(objectClass=computer)\" +
\"(objectClass=msDS-ManagedServiceAccount))\", attrs =
\[\"objectGUID\",\"distinguishedName\",\"uSNChanged\", \...\] )
allOrgNodes \<- fetchAllOrgNodes(lifecycleState != \"Archived\") adGUIDs
\<- set( obj.objectGUID for obj in allADObjects ) orgNodeGUIDs \<- set(
node.sourceAnchor for node in allOrgNodes ) orphans \<- orgNodeGUIDs -
adGUIDs // In OrgTree but absent in AD ghosts \<- adGUIDs - orgNodeGUIDs
// In AD but absent in OrgTree for each orphan in orphans:
flagOrphan(orphan) // High severity; queue for SRE review for each ghost
in ghosts: ingestGhostObject(ghost) // Auto-provision new OrgNode for
each guid in (adGUIDs INTERSECT orgNodeGUIDs):
compareAndFlagDrift(adObjects\[guid\], orgNodes\[guid\]) //
============================================================ //
COMPARISON FUNCTION //
============================================================ function
compareAndFlagDrift(adObj, orgNode): for each trackedAttribute in
driftTrackedAttributeList: normalizedADValue \<-
normalize(adObj\[trackedAttribute\]) storedOrgNodeValue \<-
orgNode\[trackedAttribute\] if normalizedADValue != storedOrgNodeValue:
driftRecord \<- recordDrift( orgNode = orgNode, field =
trackedAttribute, adValue = normalizedADValue, storedValue =
storedOrgNodeValue ) if autoRemediate(trackedAttribute):
applySyncUpdate(orgNode, trackedAttribute, normalizedADValue)
driftRecord.autoRemediated \<- true else: raiseDriftAlert(orgNode,
trackedAttribute, driftRecord)

### 8.4 Drift Alert Schema

{ \"alertId\": \"7c8d9e0f-1a2b-3c4d-5e6f-7a8b9c0d1e2f\", \"alertType\":
\"OrgTree.DriftDetected\", \"driftCategory\": \"LifecycleMismatch\",
\"severity\": \"Critical\", \"orgNodeId\":
\"a1b2c3d4-e5f6-7a8b-9c0d-e1f2a3b4c5d6\", \"displayName\": \"Jane
Smith\", \"field\": \"lifecycleState\", \"adValue\": \"Disabled
(ACCOUNTDISABLE=1)\", \"orgTreeValue\": \"Active\", \"detectedAt\":
\"2026-05-07T17:49:00Z\", \"detectionCycle\": \"fast_cycle\",
\"autoRemediated\": true, \"remediationAction\": \"LifecycleTransition:
Active -\> Suspended\", \"remediationAt\": \"2026-05-07T17:49:05Z\",
\"auditTrailRef\": \"audit-event-id-9f8e7d6c5b4a\" }

## 9. Group Ingestion & Role Mapping

### 9.1 Group Type Resolution

The AD groupType attribute is a signed 32-bit integer bitmask that
encodes both group scope and category. The table below defines the
complete decoding matrix and the corresponding OrgTree classification
assigned to each combination. The sign bit (0x80000000) indicates a
security group.

  -------------------------------------------------------------------------------------------
  **groupType    **Group     **Group        **OrgTree              **Notes**
  Value**        Scope**     Category**     Classification**
  -------------- ----------- -------------- ---------------------- --------------------------
  -2147483646    Global      Security       OrgSecurityGroup       Most common classification
  (0x80000002)                                                     for user role and access
                                                                   groups

  -2147483644    Domain      Security       OrgResourceGroup       Used for resource access
  (0x80000004)   Local                                             control (file shares,
                                                                   printers, applications)

  -2147483640    Universal   Security       OrgUniversalGroup      Cross-domain access;
  (0x80000008)                                                     primary group type in
                                                                   multi-forest deployments

  2              Global      Distribution   OrgDistributionGroup   Email-only; no security
                                                                   context; no access rights
                                                                   assignment

  4              Domain      Distribution   OrgDistributionGroup   Email-only; local
                 Local                                             distribution scope

  8              Universal   Distribution   OrgDistributionGroup   Email-only; cross-domain
                                                                   distribution; common in
                                                                   Exchange Online scenarios
  -------------------------------------------------------------------------------------------

### 9.2 Membership Flattening

Active Directory permits nested group membership --- groups containing
other groups --- to arbitrary depth. For OrgTree and downstream
access-control consumers, two distinct membership representations are
maintained:

18. **Direct membership** --- The set of groups to which an object is
    directly assigned via its memberOf attribute. Stored in
    OrgNode.groupMemberships\[\].

19. **Effective membership (transitive closure)** --- The complete
    flattened set of all groups an object belongs to, including
    groups-of-groups at any depth. Computed via breadth-first search
    (BFS) from each direct group upward through its memberOf chain.
    Stored in OrgNode.effectiveGroupMemberships\[\].

Implementation requirements for membership flattening:

- **Cycle detection:** AD permits circular group nesting (Group A member
  of Group B, Group B member of Group A). The BFS traversal must
  maintain a visited set and break on revisit. Log a warning when a
  cycle is detected, including the cycle path for investigation.

- **Maximum nesting depth:** Configurable limit (default: 10 levels).
  Objects at nesting depth greater than the maximum are treated as if
  they are not members of the groups beyond that depth. A warning is
  logged and the driftFlags array on the affected group OrgNode is
  updated with MEMBERSHIP_DEPTH_EXCEEDED.

- **Recomputation trigger:** Effective memberships must be recomputed
  for all transitive members whenever any group\'s direct member list
  changes.

### 9.3 Role-to-OrgPath Inference

Security groups whose AD DN places them within a functional
organizational OU can be used to infer an OrgPath association, enabling
downstream role-based access decisions that are contextually anchored to
the organizational hierarchy. This inference is advisory and does not
replace explicit group-to-resource mapping.

function inferGroupOrgPath(groupOrgNode): // Resolve the OU that
directly contains this group in AD parentOU \<-
resolveParentOU(groupOrgNode.sourceDN) if parentOU is not null AND
parentOU.nodeType == \"OrgUnit\" AND parentOU.orgPath is not stale AND
parentOU.lifecycleState in (\"Active\", \"Provisioned\"): // Anchor
group OrgPath under its containing OU with a /groups/ infix
groupOrgNode.inferredOrgPath \<- parentOU.orgPath + \"/groups/\" +
normalizeSegment(groupOrgNode.groupName) else: // Fall back to ungrouped
path for groups without a clear OU home groupOrgNode.inferredOrgPath \<-
\"/corp/groups/ungrouped/\" + normalizeSegment(groupOrgNode.groupName)
// Note: inferredOrgPath is stored separately from the structural
orgPath // and is labelled \"inferred\" in all downstream event payloads
return groupOrgNode.inferredOrgPath

## 10. Downstream Readiness

### 10.1 Consuming Systems Registry

  -------------------------------------------------------------------------------------------------------------------
  **Consuming        **Integration   **Key OrgTree Fields         **Sync          **Auth         **Notes**
  System**           Protocol**      Consumed**                   Frequency**     Method**
  ------------------ --------------- ---------------------------- --------------- -------------- --------------------
  **Microsoft Entra  SCIM 2.0 /      orgNodeId, upn, displayName, Every 2 minutes Provisioning   OU scoping rules map
  ID**               Microsoft Entra groupMemberships,            (event-driven   Agent outbound to Entra sync scope;
                     Cloud Sync      lifecycleState, department,  delta)          mTLS           orgPath used to
                                     jobTitle                                                    filter sync
                                                                                                 boundaries

  **ITSM (ServiceNow REST Webhook +  displayName, primaryEmail,   Real-time on    OAuth 2.0      Used for ticket
  / Jira)**          SCIM            department, managerRef,      lifecycle       Client         routing, CMDB
                                     officeLocation,              change; full    Credentials    population,
                                     lifecycleState               sync every 24h                 onboarding and
                                                                                                 offboarding
                                                                                                 workflows

  **HRIS             Outbound CSV    employeeId, displayName,     Daily batch +   SFTP (batch)   Bidirectional: HRIS
  Reconciliation**   batch / REST    department, jobTitle,        real-time delta or API key     is authoritative
                     API delta       lifecycleState, orgPath      for lifecycle   (REST)         source for
                                                                  events                         employeeId and
                                                                                                 canonical department
                                                                                                 names

  **SaaS SSO (Okta / SCIM 2.0        upn, groupMemberships,       Real-time on    Bearer Token   Effective group
  Ping Identity)**                   effectiveGroupMemberships,   change event                   memberships drive
                                     lifecycleState                                              application
                                                                                                 entitlement;
                                                                                                 Deprovisioned state
                                                                                                 triggers
                                                                                                 de-provisioning in
                                                                                                 SSO

  **Audit / SIEM**   Event stream    All lifecycle events, drift  Real-time       Managed        SOX/HIPAA/PCI
                     (Kafka / Azure  alerts, OrgPath changes,     streaming       Identity / SAS compliance log
                     Event Hub)      schema changes               (sub-second)    Token          trail; orgPath
                                                                                                 included in every
                                                                                                 event envelope for
                                                                                                 context

  **PAM (Privileged  REST API +      OrgServiceIdentity nodes,    Real-time on    mTLS + API Key Detects privilege
  Access)**          Webhook         admin group memberships,     change                         escalation via group
                                     lifecycleState,                                             membership drift;
                                     effectiveGroupMemberships                                   all
                                                                                                 OrgServiceIdentity
                                                                                                 changes are
                                                                                                 high-priority events

  **Data Catalog     REST API        orgPath, dataClassification, Daily full sync OAuth 2.0      Maps orgPath to data
  (Microsoft                         complianceTags, department                                  asset ownership
  Purview)**                                                                                     lineage; inherits
                                                                                                 dataClassification
                                                                                                 from OrgUnit for
                                                                                                 data governance
  -------------------------------------------------------------------------------------------------------------------

### 10.2 Entra ID Sync Field Mapping

  -----------------------------------------------------------------------------------
  **OrgTree Field**  **Entra ID Attribute**         **Sync        **Conflict
                                                    Direction**   Resolution**
  ------------------ ------------------------------ ------------- -------------------
  orgNodeId          onPremisesImmutableId          OrgTree →     OrgTree wins
  (sourceAnchor)                                    Entra         (immutable; set
                                                                  once on
                                                                  provisioning, never
                                                                  updated)

  upn                userPrincipalName              OrgTree →     OrgTree wins; UPN
                                                    Entra         changes emit
                                                                  downstream
                                                                  notification to all
                                                                  consumers

  displayName        displayName                    OrgTree →     OrgTree wins
                                                    Entra

  primaryEmail       mail                           OrgTree →     Entra may populate
                                                    Entra         if blank in OrgTree
                                                                  (mail-only cloud
                                                                  accounts);
                                                                  otherwise OrgTree
                                                                  wins

  department         department                     OrgTree →     OrgTree wins
                                                    Entra         (HRIS-normalized
                                                                  canonical value)

  jobTitle           jobTitle                       OrgTree →     OrgTree wins
                                                    Entra

  managerRef         manager                        OrgTree →     OrgTree wins;
  (resolved to UPN)                                 Entra         resolved by looking
                                                                  up manager\'s upn
                                                                  from their OrgNode

  officeLocation     officeLocation                 OrgTree →     OrgTree wins
                                                    Entra

  phoneNumber        mobilePhone / telephoneNumber  OrgTree →     OrgTree wins; E.164
                                                    Entra         format enforced

  lifecycleState =   accountEnabled = false         OrgTree →     OrgTree wins;
  Deprovisioned                                     Entra         Suspended also sets
                                                                  accountEnabled =
                                                                  false

  groupMemberships   memberOf                       OrgTree →     OrgTree wins; Entra
                                                    Entra         group membership is
                                                                  fully managed by
                                                                  OrgTree sync

  sid                onPremisesSecurityIdentifier   OrgTree →     Read-only in Entra;
                                                    Entra         sourced from AD via
                                                                  OrgTree; never
                                                                  modified by Entra

  orgPath            extensionAttribute_orgPath     OrgTree →     OrgTree wins;
                     (custom schema extension)      Entra         requires custom
                                                                  attribute
                                                                  registration in
                                                                  Entra ID schema
  -----------------------------------------------------------------------------------

### 10.3 Consumer Event Contract

All downstream consumers subscribe to OrgTree change events via a
**CloudEvents 1.0** compliant event envelope. The event payload is
structured as follows, with per-consumer field filtering applied at the
publisher layer. Consumers must be prepared to handle partial
changedFields payloads and must not assume all fields are present in
every event.

{ \"specversion\": \"1.0\", \"type\": \"com.orgtree.node.changed\",
\"source\": \"https://orgtree.internal/ad-integration\", \"id\":
\"9a8b7c6d-5e4f-3a2b-1c0d-9e8f7a6b5c4d\", \"time\":
\"2026-05-07T17:49:00Z\", \"datacontenttype\": \"application/json\",
\"data\": { \"orgNodeId\": \"a1b2c3d4-e5f6-7a8b-9c0d-e1f2a3b4c5d6\",
\"changeType\": \"Updated\", \"changedFields\": \[\"department\",
\"orgPath\", \"lifecycleState\"\], \"previousValues\": { \"department\":
\"Engineering\", \"lifecycleState\": \"Active\" }, \"currentValues\": {
\"department\": \"Platform Engineering\", \"orgPath\":
\"/corp/employees/platform_engineering/jsmith\", \"lifecycleState\":
\"Active\" }, \"orgPath\":
\"/corp/employees/platform_engineering/jsmith\", \"previousOrgPath\":
\"/corp/employees/engineering/jsmith\", \"lifecycleState\": \"Active\",
\"sourceDomain\": \"corp.internal\", \"eventSequence\": 1042891 } }

## 11. Implementation Runbook

### 11.1 Pre-Flight Checklist

All checklist items must be verified and signed off by the responsible
team before proceeding to the next phase. Do not begin Phase 2 ingestion
until all Phase 0 and Phase 1 items are complete.

**Phase 0 --- Prerequisites**

- AD DS forest functional level confirmed at Windows Server 2016 minimum

- AD Recycle Bin enabled on all in-scope domains (required for
  restoration event detection)

- DirSync / AD Replication USN tracking confirmed operational on all
  target domain controllers

- LDAP/S endpoint accessible from Ingestion Adapter host on port 636
  with TLS certificate validated

- Ingestion service account created with Read access to all OUs in
  scope; zero write permissions confirmed

- objectGUID confirmed to be unique and stable across all target AD
  domains

- extensionAttribute1--15 usage documented for each domain; attribute
  conflicts across domains identified and resolved

- Maximum OU depth measured across all target OUs; confirmed to be 10
  levels or fewer

- AD replication topology documented; inter-site replication latency
  measured and acceptable

**Phase 1 --- Schema Registration**

- OrgNode JSON schema (§4.1) validated against representative test data
  set covering all node types

- orgpath_history ledger table created with correct DDL and indexes
  applied

- orgtree_closure table created with correct DDL, constraints, and
  indexes applied

- DepartmentNormalizationTable populated from HRIS canonical department
  list (sourced from HRIS team)

- JobTitleCatalog populated and cross-referenced against current AD
  title values

- OfficeCatalog populated from facilities management office list with
  canonical location codes

- DisabledOUPattern regex authored and tested against all known
  deprovisioning OU paths

- ExtensionAttributeConfig YAML authored for all 15 extension attributes
  across all in-scope domains

- Schema version control process initialized in source control; initial
  version tagged as v1.0

**Phase 2 --- Initial Ingestion**

- Full LDAP read executed for all object classes in priority order: OUs
  first, then users, groups, computers, service accounts, contacts

- OrgTree nodes provisioned and verified: OUs → Groups → Users →
  Computers → Service Accounts → Contacts

- Closure table fully populated; verified via sample ancestor and
  subtree queries against known AD structure

- OrgPath computed for all nodes; sample paths validated against
  expected values by AD Operations team

- Inheritance resolution executed for all OrgUnit subtrees; inherited
  attributes spot-checked

- Lifecycle state assigned to all nodes based on current AD account
  state predicates

- Initial drift baseline snapshot stored; deep reconciliation run count
  = 0

- Total node counts reconciled: AD object count vs. OrgNode count ---
  delta less than 0.1%

**Phase 3 --- Integration Activation**

- Fast drift cycle (120s) activated; USN tracking confirmed operational
  per domain controller

- Deep reconciliation cycle (4h) scheduled and first run verified
  successful

- Lifecycle FSM activated; all five transition paths exercised in
  non-production environment

- OrgPath cache invalidation tested for all three scenarios: rename,
  move, delete

- Downstream consumers connected in order: Audit/SIEM → Entra ID → ITSM
  → SaaS SSO → PAM → Data Catalog

- Consumer event contract validated end-to-end for each consumer type
  with confirmed acknowledgment

- Drift alert routing configured to SIEM and on-call channel; test alert
  delivered successfully

- Rollback plan documented and reviewed by SRE team

**Phase 4 --- Steady-State Operations**

- Drift dashboard live with real-time severity counts; thresholds tuned
  against observed baseline

- Orphan review SLA defined and published: default 72 hours to resolve
  or escalate

- Quarterly full-reconciliation report template automated and scheduled

- Schema version control process documented; change approval gate (IAM +
  AD Ops + SRE) in place

- Runbook reviewed and signed off by SRE, AD Operations, IAM
  Engineering, and downstream system owners

- Operational runbook stored in team wiki with on-call escalation path
  documented

### 11.2 Key Configuration Reference

ad_integration: domains: - fqdn: corp.internal netbios: CORP ldap_uri:
ldaps://dc01.corp.internal:636 service_account:
svc_orgtree_read@corp.internal sync_scope_ous: -
\"OU=Employees,DC=corp,DC=internal\" -
\"OU=Contractors,DC=corp,DC=internal\" -
\"OU=ServiceAccounts,DC=corp,DC=internal\" -
\"OU=Computers,DC=corp,DC=internal\" disabled_ou_pattern:
\"OU=Disabled.\*\" system_ou_whitelist: \[\] \# GUIDs of system OUs to
include; empty = exclude all ingestion: fast_cycle_interval_seconds: 120
deep_cycle_interval_hours: 4 max_ou_depth: 10 batch_size: 500
dirsync_cookie_store: \"redis://cache.internal:6379/0\"
dirsync_cookie_key_prefix: \"orgtree:dirsync:\" normalization:
department_normalization_table: \"config/dept_normalization.json\"
job_title_catalog: \"config/job_title_catalog.json\" office_catalog:
\"config/office_catalog.json\" extension_attribute_config:
\"config/ext_attr_mapping.yaml\" unicode_normalization_form: \"NFC\"
max_segment_length: 64 max_orgpath_length: 2048 lifecycle:
grace_window_days: 90 \# Suspended -\> Deprovisioned threshold
retention_days: 365 \# Deprovisioned -\> Archived threshold
orphan_auto_deprovision_hours: 72 \# Auto-deprovision orphans after this
window drift: fast_cycle_stale_threshold_minutes: 10
max_group_nesting_depth: 10 orphan_severity: high ghost_severity: high
lifecycle_mismatch_severity: critical attribute_drift_auto_remediate:
true path_drift_auto_remediate: true lifecycle_mismatch_auto_remediate:
true group_membership_drift_auto_remediate: true orphan_auto_remediate:
false \# Requires manual SRE approval downstream: consumers: - id:
entra_id protocol: scim2 endpoint:
\"https://provisioning.microsoft.com/scim/v2/\...\" sync_mode:
event_driven_delta auth: provisioning_agent_mtls field_filter:
\[orgNodeId, upn, displayName, department, jobTitle, managerRef,
officeLocation, groupMemberships, lifecycleState\] - id: servicenow
protocol: webhook_rest endpoint:
\"https://company.service-now.com/api/orgtree/ingest\" sync_mode:
realtime_lifecycle_plus_daily_full auth: oauth2_client_credentials
field_filter: \[displayName, primaryEmail, department, managerRef,
officeLocation, lifecycleState, orgPath\] - id: audit_siem protocol:
eventhub_stream endpoint:
\"Endpoint=sb://orgtree-events.servicebus.windows.net/\...\" sync_mode:
realtime_streaming auth: managed_identity field_filter: all \# No
filtering; all fields sent to SIEM - id: okta_sso protocol: scim2
endpoint: \"https://company.okta.com/scim/v2\" sync_mode:
event_driven_delta auth: bearer_token field_filter: \[upn,
groupMemberships, effectiveGroupMemberships, lifecycleState\] - id:
pam_platform protocol: webhook_rest endpoint:
\"https://pam.internal/api/v1/orgtree/events\" sync_mode:
realtime_lifecycle_and_membership auth: mtls_plus_api_key field_filter:
\[orgNodeId, nodeType, effectiveGroupMemberships, lifecycleState,
driftFlags\] - id: purview_catalog protocol: rest_api endpoint:
\"https://company-purview.purview.azure.com/catalog/api/v2\" sync_mode:
daily_full_sync auth: oauth2_client_credentials field_filter: \[orgPath,
dataClassification, complianceTags, department, orgNodeId\]

## 12. Governance, Security & Compliance

### 12.1 Data Sensitivity Classification

  -----------------------------------------------------------------------------------------------------------
  **OrgNode Field**  **Sensitivity   **Retention**      **Masking in Logs?**       **Export Restriction**
                     Level**
  ------------------ --------------- ------------------ -------------------------- --------------------------
  orgNodeId          Internal        Indefinite         No                         Unrestricted within
                                     (primary key)                                 organization

  displayName        Internal        7 years            No                         Unrestricted within
                                     post-archival                                 organization

  primaryEmail       Internal        7 years            No                         Restricted: no external
                                                                                   export without DLP review
                                                                                   and approval

  employeeId         Confidential    7 years            Yes (partial masking: show Restricted: HR and finance
                                                        last 4 digits only)        systems only; no external
                                                                                   export

  sid                Confidential    Indefinite         Yes (masked in application Restricted: IAM and
                                                        logs; visible in audit     security systems only
                                                        logs only)

  accountStatus      Internal        7 years            No                         Restricted: IAM, ITSM, and
  flags                                                                            PAM systems only

  customAttributes   Varies by       Varies by          Depends on                 Depends on classification
                     attribute       attribute          ExtensionAttributeConfig   tag assigned in
                                                        classification tag         ExtensionAttributeConfig

  orgPath            Internal        Indefinite (via    No                         Unrestricted within
                                     orgpath_history)                              organization; included in
                                                                                   all event payloads
  -----------------------------------------------------------------------------------------------------------

### 12.2 RBAC Model for OrgTree API

  -----------------------------------------------------------------------------------------------------
  **Role**                      **Read    **Read      **Write / Sync**      **Approve       **Admin**
                                All       Sensitive                         Orphan
                                Nodes**   Fields**                          Remediation**
  ----------------------------- --------- ----------- --------------------- --------------- -----------
  **OrgTree.Reader**            Yes       No          No                    No              No

  **OrgTree.SensitiveReader**   Yes       Yes         No                    No              No

  **OrgTree.SyncAgent**         Yes       Yes         Yes (sync operations  No              No
                                                      only; no manual
                                                      writes)

  **OrgTree.DriftApprover**     Yes       No          No                    Yes             No

  **OrgTree.Admin**             Yes       Yes         Yes                   Yes             Yes
  -----------------------------------------------------------------------------------------------------

+----------------------------------------------------------------------+
| **⚠ Principle of Least Privilege**                                   |
|                                                                      |
| The AD ingestion service account must hold only OrgTree.SyncAgent    |
| role. No human operator should be assigned OrgTree.Admin in          |
| production environments without a formal access request,             |
| time-bounded approval, and session recording enabled.                |
+----------------------------------------------------------------------+

### 12.3 Audit Trail Requirements

The following events must be captured in the immutable, append-only
audit log. The audit log must be stored in a tamper-evident, write-once
storage system (e.g., Azure Immutable Blob Storage with WORM policy, AWS
S3 Object Lock, or equivalent). No update or delete operations are
permitted on audit log entries under any circumstances.

- Every OrgNode create, update, or delete operation, with full
  before/after attribute diff

- Every lifecycle state transition, including the triggering agent
  identity, reason code, and timestamp

- Every OrgPath change, with old and new path values and the triggering
  event

- Every drift detection event with drift category, severity, field
  values, and remediation outcome

- Every downstream consumer notification with consumer ID, payload hash,
  and acknowledgment status (delivered / failed / retrying)

- Every schema configuration change with full before/after diff and
  approver identity

- Every RBAC role assignment or revocation for OrgTree API roles

- Every orphan remediation approval or rejection with approver identity
  and reason

**Retention:** Minimum 7 years from event creation date. Audit logs must
be queryable by orgNodeId, orgPath, time range, event type, and agent
identity. Legal hold must be supportable by suspending scheduled
deletion for named records.

## 13. Reference: Key Formulas & Identifiers

### 13.1 Unique Key Summary

The table below summarizes all identifier types used within the OrgTree
integration, their source, stability characteristics, and usage
guidance. Implementers must use orgNodeId (derived from AD objectGUID)
as the primary stable reference in all inter-system integrations.
OrgPath is for human-readable display and organizational context only
--- never for stable programmatic references.

  -------------------------------------------------------------------------------------------------------
  **Identifier**   **Source**            **Uniqueness          **Immutable?**    **Notes & Usage
                                         Guarantee**                             Guidance**
  ---------------- --------------------- --------------------- ----------------- ------------------------
  **orgNodeId**    AD objectGUID         Global across all     **Yes**           Primary key for all
                   (reformatted as UUID  domains and forests                     inter-system references.
                   v4)                   in scope                                Never reuse even after
                                                                                 archival. Use this ---
                                                                                 not DN or UPN --- for
                                                                                 all stable API
                                                                                 references.

  **sid**          AD objectSid (binary  Domain-scoped unique; Yes (within       Secondary lookup key.
                   → S-1-5-21-\...       unique across the     domain)           Survives domain
                   string)               forest via SID                          migrations via SID
                                         history                                 history. Useful for
                                                                                 legacy systems that
                                                                                 still use SID-based
                                                                                 ACLs.

  **orgPath**      Computed from OrgTree Unique at a given     **No** (changes   Use for human-readable
                   closure table         point in time within  on rename or      display, organizational
                   traversal             the OrgTree           move)             context in events, and
                                                                                 Data Catalog lineage.
                                                                                 Never use as a stable
                                                                                 programmatic key. Always
                                                                                 use orgNodeId for stable
                                                                                 references.

  **upn**          AD userPrincipalName  Forest-unique         No (changeable;   Login identifier for
                                                               e.g., on surname  authentication flows.
                                                               or domain change) All UPN changes must
                                                                                 trigger downstream
                                                                                 notification. Do not use
                                                                                 as a stable integration
                                                                                 key; use orgNodeId.

  **employeeId**   HRIS (anchored in AD  Organization-unique   Yes               Cross-system anchor for
                   via                   (HRIS-assigned)       (HRIS-assigned;   HRIS reconciliation.
                   extensionAttribute)                         should never      Bidirectional key: HRIS
                                                               change)           is authoritative source.
                                                                                 Use to correlate AD
                                                                                 identities with HRIS
                                                                                 records for
                                                                                 joiners/movers/leavers
                                                                                 workflows.

  **sourceDN**     AD distinguishedName  Domain-unique at a    **No** (changes   Stored as informational
                                         point in time         on every OU move  context only. Never use
                                                               or rename)        as a primary or foreign
                                                                                 key in any system.
                                                                                 Subject to change on any
                                                                                 structural AD
                                                                                 modification.

  **loginName**    AD sAMAccountName     Domain-unique         No (changeable by Used as leaf segment in
                                                               AD admin)         OrgPath for user nodes.
                                                                                 Changes to
                                                                                 sAMAccountName trigger
                                                                                 OrgPath recomputation
                                                                                 and downstream
                                                                                 notification.
  -------------------------------------------------------------------------------------------------------

+----------------------------------------------------------------------+
| **ℹ Document End --- Implementation Handoff**                        |
|                                                                      |
| This document represents the complete v1.0 specification for the AD  |
|                                                                      |
| →                                                                    |
|                                                                      |
| OrgTree/OrgPath integration. All sections are implementation-ready.  |
| Questions, change requests, and errata should be submitted to the    |
| Enterprise Architecture                                              |
|                                                                      |
| &                                                                    |
|                                                                      |
| IAM Engineering team via the standard RFC process. Schema changes    |
| require version bump and downstream consumer notification with a     |
| minimum 30-day deprecation notice.                                   |
+----------------------------------------------------------------------+

**AD→OrgTree/OrgPath Integration Blueprint** \| Version 1.0 \| May 7,
2026\
Enterprise Architecture & IAM Engineering \| Classification: Internal
--- Confidential\
This document is maintained under version control. Refer to the document
registry for the authoritative current version.
