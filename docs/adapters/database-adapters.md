# **UIAO-Core Database Adapters**  
### **Canonical Definition — Version 1.0**

Database Adapters provide the **deterministic, provenance‑first integration layer** between UIAO-Core and any system that exposes structured or semi‑structured data through a database interface. They ensure that UIAO can extract, normalize, validate, and publish authoritative claims without requiring direct coupling to vendor‑specific schemas, drivers, or operational models.

This document defines the **responsibility domains**, **required behaviors**, **adapter contract**, and **vendor implementation guidance** for all Database Adapters in UIAO-Core.

---

# **1.0 Purpose and Scope**

Database Adapters enable UIAO to:

- Connect to relational, document, graph, or key‑value databases  
- Extract authoritative data with deterministic provenance  
- Normalize vendor‑specific schemas into UIAO canonical structures  
- Enforce claims‑not‑copies discipline  
- Provide drift‑resistant, reproducible evidence for KSIs  
- Support continuous monitoring and automated ATO workflows  

Database Adapters are **not ORMs**, **not ETL pipelines**, and **not data sync tools**. They are **provenance‑first extraction modules** that expose **claims**, not data copies.

---

# **2.0 Responsibility Domains**

Database Adapters must implement **all seven responsibility domains**. These domains define the canonical contract for any database integration within UIAO-Core.

---

## **2.1 Connection & Identity Domain**

The adapter must:

- Establish a secure, authenticated connection using **least‑privilege service principals**  
- Support **mTLS**, **token‑based authentication**, or **federated identity**  
- Enforce **no embedded credentials** (use managed identity or secret providers)  
- Emit a **ConnectionProvenance** envelope containing:
  - authentication method  
  - identity used  
  - connection timestamp  
  - endpoint metadata  
  - TLS/mTLS parameters  

**Example (Python):**

```python
conn = adapter.connect()
assert conn.provenance.identity == "uiao-managed-identity"
```

---

## **2.2 Schema Discovery & Canonical Mapping Domain**

The adapter must:

- Discover vendor schemas (tables, collections, indexes, constraints)  
- Map vendor structures to **UIAO canonical entities**  
- Emit a **SchemaMappingObject** containing:
  - vendor schema  
  - canonical schema  
  - mapping rules  
  - unmapped fields  
  - version hash  

This ensures UIAO can reason about data **without vendor lock‑in**.

**Example Mapping Table:**

| Vendor Field | Canonical Field | Notes |
|--------------|-----------------|-------|
| `user_id` | `subject.id` | Direct mapping |
| `last_login_ts` | `subject.last_authentication` | Timestamp normalization |
| `role_list` | `subject.roles[]` | Array expansion |

---

## **2.3 Query Normalization & Deterministic Extraction Domain**

The adapter must:

- Accept **canonical query definitions** (UIAO Query DSL)  
- Translate them into vendor‑specific SQL/NoSQL queries  
- Guarantee **deterministic, reproducible extraction**  
- Emit a **QueryProvenance** envelope containing:
  - canonical query  
  - vendor query  
  - execution plan hash  
  - row count  
  - execution timestamp  

**Example Canonical Query:**

```yaml
select:
  - subject.id
  - subject.last_authentication
from: identity_subjects
where:
  - subject.status = "active"
```

---

## **2.4 Data Normalization & Claim Construction Domain**

The adapter must:

- Convert raw database rows/documents into **UIAO ClaimObjects**  
- Normalize timestamps, identifiers, and enumerations  
- Enforce **claims‑not‑copies** discipline:
  - No replication of full records  
  - Only emit **minimal, authoritative claims**  
- Produce a **ClaimSet** with:
  - claim_id  
  - canonical entity  
  - canonical fields  
  - provenance hash  
  - source reference  

**Example ClaimObject:**

```json
{
  "claim_id": "claim-12345",
  "entity": "identity.subject",
  "fields": {
    "id": "A123",
    "last_authentication": "2026-03-31T14:22:00Z"
  },
  "source": "postgresql://id-db/users",
  "provenance_hash": "abc123..."
}
```

---

## **2.5 Drift Detection & Version Integrity Domain**

The adapter must detect:

- Schema drift  
- Constraint drift  
- Data shape drift  
- Query plan drift  
- Cardinality drift  

It must emit a **DriftReport** containing:

- drift type  
- severity  
- first observed timestamp  
- last observed timestamp  
- recommended remediation  

**Example Drift Types:**

| Drift Type | Description |
|------------|-------------|
| Schema Drift | Column added/removed/renamed |
| Constraint Drift | PK/FK/index changes |
| Cardinality Drift | Row count deviates from expected range |
| Semantics Drift | Field meaning changes (e.g., enum values) |

---

## **2.6 Evidence Packaging & KSI Integration Domain**

The adapter must produce evidence suitable for:

- **KSI validation**  
- **OSCAL observation generation**  
- **Quarto dashboard rendering**  

Each extraction must emit an **EvidenceObject** containing:

- ksi_id  
- source  
- timestamp  
- raw_data (minimal)  
- normalized_data  
- provenance  
- freshness_valid  

This aligns with the **KSI Evidence Bundle Schema**.

---

## **2.7 Security, Privacy, and Operational Controls Domain**

The adapter must enforce:

- No PII expansion  
- No unbounded queries  
- No cross‑tenant leakage  
- TLS/mTLS enforcement  
- Query timeouts  
- Row count limits  
- Audit logging  

It must also support:

- **FIPS‑validated crypto**  
- **FedRAMP Moderate/High boundary constraints**  
- **UIAO Leakage Prevention Controls**  

---

# **3.0 Comparison Table — Database Adapters vs Other Adapter Types**

| Capability | Database Adapter | API Adapter | Log Adapter | File Adapter |
|-----------|------------------|-------------|-------------|--------------|
| Schema Discovery | **Yes** | Partial | No | No |
| Canonical Mapping | **Yes** | Yes | Minimal | Minimal |
| Deterministic Extraction | **Yes** | Yes | No (event‑driven) | Yes |
| Drift Detection | **Full** | Partial | No | No |
| Claim Construction | **Yes** | Yes | Yes | Yes |
| Query Normalization | **Yes** | No | No | No |
| Evidence Packaging | **Yes** | Yes | Yes | Yes |
| KSI Integration | **Full** | Full | Full | Full |
| Operational Complexity | Medium | Medium | Low | Low |
| Vendor Variability | High | High | Medium | Low |

Database Adapters are the **most structured** and **most deterministic** adapter type in UIAO-Core.

---

# **4.0 Vendor Implementation Guidance**

This section provides prescriptive guidance for database vendors integrating with UIAO-Core.

---

## **4.1 Required Capabilities**

Vendors must provide:

- A stable, documented schema  
- Deterministic query semantics  
- Metadata endpoints for schema discovery  
- Support for:
  - TLS 1.2+  
  - mTLS (preferred)  
  - Token‑based authentication  
  - Least‑privilege roles  
- Ability to return **minimal, filtered datasets**  

---

## **4.2 Recommended Capabilities**

Vendors should provide:

- Schema versioning  
- Query plan hashing  
- Change data capture (CDC) feeds  
- Row‑level security (RLS)  
- Built‑in drift detection signals  

---

## **4.3 Anti‑Patterns to Avoid**

Vendors must **not**:

- Require admin‑level credentials  
- Require full‑table scans  
- Return unbounded datasets  
- Obscure schema metadata  
- Use proprietary timestamp formats  
- Break deterministic ordering  

---

## **4.4 Example Vendor Integration Pattern**

**Step 1 — Provide a metadata endpoint**

```json
{
  "tables": [
    {
      "name": "users",
      "columns": [
        {"name": "id", "type": "uuid"},
        {"name": "last_login", "type": "timestamp"},
        {"name": "roles", "type": "jsonb"}
      ]
    }
  ]
}
```

**Step 2 — Provide a deterministic query interface**

```sql
SELECT id, last_login, roles
FROM users
WHERE status = 'active'
ORDER BY id ASC;
```

**Step 3 — Provide a stable identity model**

- Service principal  
- mTLS client certificate  
- Token‑based authentication  

**Step 4 — Provide drift signals**

- Schema version  
- Column hash  
- Index metadata  

---

# **5.0 Adapter Contract (Normative)**

Every Database Adapter must implement:

### **5.1 Methods**
- `connect() -> ConnectionProvenance`  
- `discover_schema() -> SchemaMappingObject`  
- `execute_query(canonical_query) -> QueryProvenance`  
- `normalize(raw_rows) -> ClaimSet`  
- `detect_drift() -> DriftReport`  
- `collect_evidence(ksi_id) -> EvidenceObject`  

### **5.2 Guarantees**
- Deterministic extraction  
- Provenance‑first design  
- No data replication  
- No schema inference at runtime  
- No vendor‑specific leakage into canonical layers  

---

# **6.0 Example Adapter Skeleton**

```python
class PostgresAdapter(DatabaseAdapterBase):

    ADAPTER_ID = "postgres"

    def connect(self):
        # mTLS or token-based connection
        ...

    def discover_schema(self):
        # Query information_schema
        ...

    def execute_query(self, canonical_query):
        # Translate UIAO DSL -> SQL
        ...

    def normalize(self, rows):
        # Convert rows -> ClaimSet
        ...

    def detect_drift(self):
        # Compare schema hash to previous version
        ...

    def collect_evidence(self, ksi_id):
        # Produce EvidenceObject
        ...
```

---

# **7.0 Testing & Validation Requirements**

Database Adapters must pass:

- Schema discovery tests  
- Canonical mapping tests  
- Query translation tests  
- Drift detection tests  
- Evidence packaging tests  
- KSI integration tests  

Adapters must also include:

- Synthetic fixtures  
- Deterministic test datasets  
- Regression tests for drift detection  

---

# **8.0 Security Considerations**

Database Adapters must:

- Never log sensitive data  
- Never store raw rows outside memory  
- Use ephemeral connections  
- Enforce row limits  
- Enforce query timeouts  
- Use FIPS‑validated crypto  

---

# **9.0 Versioning & Lifecycle**

Adapters must include:

- `adapter_version`  
- `schema_version`  
- `mapping_version`  
- `provenance_hash`  

Adapters must be:

- Backwards compatible  
- Deterministic across versions  
- Fully documented  

---

# **10.0 Summary**

Database Adapters are the **canonical, deterministic, provenance‑first integration layer** for structured data in UIAO-Core. They provide:

- Schema discovery  
- Canonical mapping  
- Deterministic extraction  
- Drift detection  
- Claim construction  
- Evidence packaging  
- KSI integration  

They are essential for **continuous ATO**, **evidence automation**, and **federated modernization**.
