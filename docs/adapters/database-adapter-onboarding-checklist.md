# UIAO-Core Database Adapter Onboarding Checklist  
### Version 1.0 — Vendor & Implementer Guide

This checklist guides vendors and implementers through the complete process of creating a **new Database Adapter** for UIAO‑Core. It follows the canonical Database Adapter specification and ensures consistency, provenance integrity, and KSI compatibility.

Use this document as a **step‑by‑step implementation and validation workflow**.

---

# 1.0 Prerequisites

Before beginning development:

- [ ] You have reviewed the **UIAO Database Adapter Canonical Definition**  
- [ ] You understand the **7 Responsibility Domains**  
- [ ] You have access to a **test database instance**  
- [ ] You have credentials for a **least‑privilege service principal**  
- [ ] You can enable **TLS 1.2+** and preferably **mTLS**  
- [ ] You have installed the UIAO-Core development environment  
- [ ] You have read the **KSI Schema** and **Evidence Bundle Schema**  
- [ ] You have reviewed existing adapters (Postgres, MongoDB, etc.) for patterns  

---

# 2.0 Connection Setup

Implement secure, deterministic connection behavior:

- [ ] Implement `connect() -> ConnectionProvenance`  
- [ ] Enforce **no embedded credentials** (use managed identity or secret provider)  
- [ ] Support **TLS 1.2+**  
- [ ] Prefer **mTLS** if the vendor supports it  
- [ ] Capture identity, endpoint, TLS version, and timestamp  
- [ ] Emit a complete **ConnectionProvenance** envelope  
- [ ] Validate connection health before proceeding  

---

# 3.0 Schema Discovery Implementation

Your adapter must be able to introspect vendor schema:

- [ ] Implement `discover_schema() -> SchemaMappingObject`  
- [ ] Retrieve vendor schema metadata (tables, collections, indexes, constraints)  
- [ ] Normalize vendor schema into UIAO canonical schema  
- [ ] Identify unmapped fields  
- [ ] Generate a **version hash** for schema integrity  
- [ ] Ensure deterministic ordering of schema metadata  
- [ ] Document any vendor-specific quirks  

---

# 4.0 Canonical Mapping

Define how vendor fields map to UIAO canonical entities:

- [ ] Create a **mapping_rules** structure  
- [ ] Map vendor fields → canonical fields  
- [ ] Normalize timestamps, enums, identifiers  
- [ ] Document unmapped or partially mapped fields  
- [ ] Validate mapping with sample datasets  
- [ ] Ensure mapping is **stable across versions**  

---

# 5.0 Query Normalization

Implement deterministic query translation:

- [ ] Implement `execute_query(canonical_query) -> QueryProvenance`  
- [ ] Translate UIAO Query DSL → vendor SQL/NoSQL query  
- [ ] Ensure deterministic ordering (ORDER BY required)  
- [ ] Enforce row limits and timeouts  
- [ ] Capture execution plan hash  
- [ ] Capture row count  
- [ ] Emit a complete **QueryProvenance** envelope  

---

# 6.0 Claim Construction

Convert raw rows/documents into canonical claims:

- [ ] Implement `normalize(raw_rows) -> ClaimSet`  
- [ ] Create minimal, authoritative **ClaimObjects**  
- [ ] Enforce **claims‑not‑copies** discipline  
- [ ] Generate provenance hashes for each claim  
- [ ] Validate canonical field types  
- [ ] Ensure no sensitive fields are included  
- [ ] Produce a complete **ClaimSet**  

---

# 7.0 Drift Detection

Implement drift detection across schema, constraints, and semantics:

- [ ] Implement `detect_drift() -> DriftReport`  
- [ ] Detect schema drift (added/removed/renamed fields)  
- [ ] Detect constraint drift (PK/FK/index changes)  
- [ ] Detect cardinality drift (unexpected row count changes)  
- [ ] Detect semantics drift (enum changes, field meaning changes)  
- [ ] Emit a **DriftReport** with severity and remediation guidance  
- [ ] Ensure drift detection is deterministic and reproducible  

---

# 8.0 Evidence Packaging

Produce evidence suitable for KSI validation and OSCAL export:

- [ ] Implement `collect_evidence(ksi_id) -> EvidenceObject`  
- [ ] Package connection provenance  
- [ ] Package schema mapping  
- [ ] Package query provenance  
- [ ] Package claim set  
- [ ] Package drift report  
- [ ] Generate provenance hash for normalized data  
- [ ] Ensure evidence aligns with **evidence-bundle.schema.json**  

---

# 9.0 KSI Integration

Ensure your adapter supports UIAO continuous monitoring:

- [ ] Validate evidence freshness windows  
- [ ] Ensure evidence fields align with KSI rule expectations  
- [ ] Test integration with the **KSI Validator Engine**  
- [ ] Confirm that drift indicators surface correctly  
- [ ] Validate that evidence supports OSCAL observation generation  
- [ ] Provide sample KSI rules for your adapter’s domain  

---

# 10.0 Testing Requirements

Your adapter must include:

### Unit Tests
- [ ] Connection tests  
- [ ] Schema discovery tests  
- [ ] Query translation tests  
- [ ] Claim normalization tests  
- [ ] Drift detection tests  

### Integration Tests
- [ ] End‑to‑end evidence generation  
- [ ] KSI validation tests  
- [ ] Evidence bundle validation against schema  

### Fixtures
- [ ] Synthetic vendor datasets  
- [ ] Deterministic schema snapshots  
- [ ] Drift simulation datasets  

---

# 11.0 Security Review

Before deployment:

- [ ] Validate no sensitive data is logged  
- [ ] Validate no raw rows are persisted  
- [ ] Validate TLS/mTLS enforcement  
- [ ] Validate least‑privilege identity usage  
- [ ] Validate row limits and timeouts  
- [ ] Validate FIPS‑validated crypto usage  
- [ ] Validate no cross‑tenant leakage  
- [ ] Validate compliance with UIAO Leakage Prevention Controls  

---

# 12.0 Deployment

To finalize onboarding:

- [ ] Provide adapter documentation in `docs/adapters/<vendor>.md`  
- [ ] Register adapter in `src/uiao_core/adapters/__init__.py`  
- [ ] Provide example configuration files  
- [ ] Provide sample KSI rules  
- [ ] Provide sample evidence bundles  
- [ ] Provide Quarto dashboard screenshots  
- [ ] Submit adapter for UIAO-Core review  

---

# 13.0 Completion

Once all checklist items are complete:

- [ ] Adapter is ready for inclusion in UIAO-Core  
- [ ] Adapter is eligible for certification as a **UIAO‑Compatible Database Adapter**  
- [ ] Adapter can participate in **continuous ATO pipelines**  
- [ ] Adapter can be used in **federal modernization pilots**  

---

This checklist ensures that every Database Adapter meets the **deterministic, provenance‑first, drift‑resistant** standards required by UIAO-Core.  
