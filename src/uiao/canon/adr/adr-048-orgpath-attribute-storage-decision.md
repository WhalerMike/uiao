---
title: "Unified Identity‑Addressing‑Overlay Architecture (UIAO)"
subtitle: "Canon Volume 0 — Doctrinal Foundation"
version: "1.0"
status: "Current"
classification: "Unclassified // UIAO Canon"
document_type: "Canonical Architecture Volume"
uiao_plane: "Governance Substrate"
uiao_layer: "Doctrinal Foundation"
uiao_id: "UIAO-V0"
author: "UIAO Architecture Office"
created: "2026-04-28"
last_updated: "2026-04-28"
canonical: true
drift_allowed: false
description: >
  Establishes the doctrinal foundation, invariants, and governing principles
  for the Unified Identity‑Addressing‑Overlay Architecture (UIAO). Defines the
  substrate, membrane, and canonical rules that govern all downstream volumes,
  adapters, and modernization phases.
---


## 1. Status
PROPOSED

---

## 2. Context

OrgPath is the canonical identity hierarchy for UIAO. It encodes organizational structure as a dot‑delimited path (e.g., `UIAO.REGION.DIVISION.UNIT`) and serves as the authoritative source for governance topology placement. Every governed user principal carries an OrgPath value that enables deterministic policy targeting, delegated administration scoping, and compliance baselining.

OrgPath is consumed simultaneously by dynamic group rules, Conditional Access, Intune, ARC governance tagging, SCuBA drift detection, delegated administration, license automation, and segmentation policies. The attribute is load‑bearing; failures cascade across all dependent control surfaces.

UIAO operates in Commercial Cloud under FedRAMP. GCC‑Moderate applies only to Microsoft 365 SaaS services, not Azure. Therefore, the attribute must be fully supported, GA, and production‑hardened within GCC‑Moderate M365 tenants.

OrgPath is currently stored in `extensionAttribute1`. This ADR formalizes the evaluation and rationale. Three dependent specifications (UIAO_031, UIAO_034, UIAO_039) are blocked pending this decision.

---

## 3. Problem Statement

UIAO requires a single canonical Entra ID attribute to store the OrgPath hierarchy string. The attribute must be consumable by dynamic groups, Conditional Access, Intune, SCuBA, delegated admin, and automation pipelines — all within GCC‑Moderate. Three specifications are blocked until this decision is finalized.

---

## 4. Constraints

- GCC‑Moderate GA support
- Dynamic group compatibility
- Conditional Access consumability
- Intune readability
- Graph API read/write
- String storage up to 256 chars
- Hybrid sync compatibility
- SCuBA queryability
- Operational simplicity
- Single‑attribute determinism

---

## 5. Options Considered

### **Option A — extensionAttribute1**
- 15 predefined string attributes
- Fully supported in dynamic groups, Graph, Intune, and GCC‑Moderate
- No app registration required
- Human‑readable
- Limitation: fixed set of 15, string‑only

### **Option B — Custom Security Attributes**
- Typed, structured, RBAC‑controlled
- Not supported in dynamic groups (**hard blocker**)
- Not exposed to Intune
- Designed for access governance, not identity hierarchy

### **Option C — Directory Extensions**
- App‑registered custom attributes
- Supported in dynamic groups but require GUID‑prefixed names
- Operational overhead: app registration lifecycle
- Governance dependency risk
- Supported in GCC‑Moderate but violates operational simplicity

---

## 6. Evaluation Criteria

| Criterion | Weight | Description |
|----------|--------|-------------|
| Dynamic Group Support | Critical | Attribute usable in dynamic rules |
| Conditional Access Integration | Critical | Consumable directly or via group |
| GCC-Moderate GA Status | Critical | Fully supported in GCC-M |
| Intune Readability | High | Readable for policy assignment |
| Graph API Read/Write | High | Full CRUD |
| Operational Simplicity | High | No app registration |
| SCuBA Queryability | High | Queryable for drift detection |
| Entra Connect Sync | Medium | Hybrid sync support |
| Naming Clarity | Medium | Human-readable |
| Attribute Capacity | Low | Available slots |

---

## 7. Comparative Analysis

| Criterion | extensionAttribute1 | Custom Security Attributes | Directory Extensions |
|----------|---------------------|----------------------------|----------------------|
| Dynamic Group Support | PASS | FAIL | PASS |
| Conditional Access | PASS | PARTIAL | PASS |
| GCC-M GA | PASS | PASS | PASS |
| Intune | PASS | FAIL | PASS |
| Graph API | PASS | PASS | PASS |
| Operational Simplicity | PASS | PASS | FAIL |
| SCuBA Queryability | PASS | PARTIAL | PASS |
| Hybrid Sync | PASS | N/A | PASS |
| Naming Clarity | PASS | PASS | FAIL |
| Capacity | Moderate | PASS | PASS |
| **Overall** | **10/10** | **4/10** | **8/10** |

---

## 8. Decision

**extensionAttribute1 is selected as the canonical storage location for OrgPath.**

---

## 9. Rationale

- Universal downstream compatibility
- Zero infrastructure dependency
- GCC‑Moderate proven
- Operational transparency
- Native hybrid sync
- SCuBA alignment
- Deterministic single source
- Two decades of schema stability

---

## 10. Consequences

### **Positive**
- Unblocks UIAO_031, UIAO_034, UIAO_039
- Simple, auditable dynamic group rules
- No additional infrastructure
- SCuBA can query natively
- Delegated admin alignment
- License automation enabled

### **Negative**
- Consumes extensionAttribute1
- String‑only type
- Shared write surface
- No built‑in versioning

### **Risks & Mitigations**

| Risk | Impact | Mitigation |
|------|---------|------------|
| Attribute collision | High | Tenant attribute registry + SCuBA drift rule |
| Unauthorized modification | High | Restrict write permissions + SCuBA monitoring |
| Format corruption | Medium | Regex validation + SCuBA |
| Attribute exhaustion | Low | Monitor usage; migrate low‑value attributes |

---

## 11. Implementation Notes

- Maintain tenant attribute registry
- Write exclusively via automation pipeline
- Enforce OrgPath regex: `^UIAO(\.[A-Z0-9-]+){1,4}$`
- SCuBA drift rule for unauthorized changes
- Update dependent specs to reference UIAO_048

---

## 12. References

- Microsoft Learn: Dynamic membership rules
- Microsoft Learn: Custom security attributes
- Microsoft Learn: Directory extensions
- UIAO_031, UIAO_034, UIAO_039
- UIAO Canon: GCC‑Moderate boundary

---

## 13. Approval

| Role | Name | Date | Status |
|------|-------|--------|---------|
| Canon Steward | Michael Stratton | (pending) | PROPOSED |
| Governance Board | (pending) | (pending) | PENDING |
