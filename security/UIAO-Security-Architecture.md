# UIAO Security Architecture Layer

## Overview

The UIAO Security Architecture Layer defines how UIAO protects itself, its tenants, its evidence, its enforcement surfaces, and its provenance chain. This is the layer auditors, red teams, and federal security assessors will scrutinize most intensely.

---

## 1. Threat Model

### 1.1 Adversary Profiles

| Adversary | Goal | Primary Attack Surface |
|-----------|------|----------------------|
| Insider threat | Corrupt evidence to hide violations | Evidence Service, Data Lake |
| External attacker | Manipulate OSCAL outputs | API Gateway, OSCAL Service |
| Rogue plugin | Exfiltrate tenant data | Plugin execution environment |
| Tenant-to-tenant | Access another tenant's evidence | API Gateway, Data Lake |
| Supply chain | Compromise control packs | Control Pack Registry |
| Enforcement bypass | Prevent enforcement | Enforcement Runtime |

### 1.2 Attack Surfaces

- Evidence ingestion endpoints (SCuBA, M365, APIs)
- Evidence storage (Raw/Normalized/Curated zones)
- KSI evaluation engine
- Enforcement adapters
- OSCAL output pipeline
- API Gateway (Operator, Auditor, Plugin, Tenant)
- Plugin execution environment
- Orchestrator job queue

### 1.3 Threat Mitigations

- All evidence is write-once, append-only (no deletion)
- All evidence is hashed on write (SHA-256)
- All evidence has a provenance manifest
- All enforcement actions are logged and require explicit authorization
- All APIs are authenticated and authorization-scoped
- All plugins run in sandboxed containers
- Control packs are version-locked and integrity-checked

---

## 2. Trust Boundaries

### 2.1 Plane Trust Boundaries

Each plane is a trust boundary:

| Plane | Trust Level | Input Validation | Output Validation |
|-------|-------------|-----------------|-------------------|
| Plane 1 (Ingestion) | Low trust (external sources) | Schema + hash | Immutability enforced |
| Plane 2 (Evaluation) | Medium trust (internal) | IR schema | KSI result schema |
| Plane 3 (Bundling) | Medium trust (internal) | KSI schema | Evidence bundle schema |
| Plane 4 (OSCAL) | High trust (auditor-facing) | Evidence bundle + OSCAL schema | OSCAL validation |

### 2.2 Service Trust Boundaries

- No service reads directly from another service's storage
- All inter-service communication uses internal API contracts
- API contracts are version-pinned and schema-validated

### 2.3 Tenant Boundaries

- Per-tenant encryption keys
- Per-tenant namespaces in data lake
- Per-tenant job queues
- No cross-tenant visibility at any layer

### 2.4 Plugin Boundaries

- Plugins cannot access other plugins' data
- Plugins cannot access the host file system
- Plugins are network-restricted (whitelist only)
- Plugin output is schema-validated before acceptance

---

## 3. Identity & Access Model

### 3.1 Operator Identity

**Full access.** Can:
- Run SCuBA
- Install/remove control packs
- Manage plugins
- Trigger enforcement
- View all tenant data (with explicit scope)

**Cannot:**
- Delete evidence (no delete capability exists)
- Impersonate tenants

### 3.2 Auditor Identity

**Read-only.** Can access:
- Evidence
- Findings
- POA&M
- OSCAL artifacts

**Cannot:**
- Trigger enforcement
- Modify evidence
- Modify control packs

### 3.3 Tenant Identity

**Scoped to tenant.** Can:
- Run ingestion
- Run enforcement
- View their own OSCAL

**Cannot:**
- Access other tenants
- Modify global control packs

### 3.4 Plugin Identity

**Least-privilege.** Can only:
- Read its own config
- Write evidence for its declared source

**Cannot:**
- Read other plugins' evidence
- Trigger enforcement
- Access tenant identity tokens

---

## 4. Key Management & Cryptographic Controls

### 4.1 Evidence Hash Keys
- SHA-256 per evidence object
- Keys rotated per tenant on schedule
- Stored in tenant key vault

### 4.2 Provenance Manifest Keys
- HMAC-SHA-256 per provenance manifest
- Rotation: monthly (or on incident)

### 4.3 Tenant Encryption Keys
- AES-256-GCM per tenant data partition
- Rotation: quarterly
- HSM-backed in FedRAMP/GCC deployments

### 4.4 API Keys
- Scoped to identity role
- Short-lived (30 days max)
- Auditor API keys: read-only scope enforced at issuance

---

## 5. Data Protection

### 5.1 Evidence at Rest
- Encrypted with tenant encryption key
- Hash stored separately for integrity verification
- Retention enforced by policy (no manual deletion)

### 5.2 Evidence in Transit
- TLS 1.2+ minimum for all service-to-service communication
- mTLS for enforcement adapter communication

### 5.3 OSCAL Artifacts
- Signed with provenance manifest
- Published with integrity checksums
- Accessible via Auditor API (read-only, scoped)

### 5.4 Memory Safety
- Evidence never stored unencrypted in memory longer than required
- Enforcement adapters run in isolated sandboxes
- Plugins run in restricted containers

---

## 6. Plugin Sandboxing & Execution Safety

### 6.1 Execution Sandbox
- Containerized execution
- No host system access
- Network access limited to whitelisted endpoints only
- File system access limited to ephemeral scratch space

### 6.2 Schema Enforcement
Plugins must produce valid evidence JSON, valid metadata, and valid provenance. Invalid output causes the plugin to be automatically disabled.

### 6.3 Capability Scoping
Plugins must declare: evidence sources, controls covered, and required permissions. All declarations are validated against the Plugin Registry before execution.

---

## 7. Enforcement Safety Model

Enforcement is the highest-risk operation in UIAO.

### 7.1 Enforcement Authorization

Enforcement requires:
- Explicit EPL policy declaration
- Operator authorization per adapter
- Tenant confirmation (for production environments)
- Blast radius classification (low/medium/high)

### 7.2 Enforcement Rollback

All enforcement adapters must declare rollback capability. Advisory-only mode available as fallback for adapters without rollback.

### 7.3 Enforcement Audit Trail

All enforcement actions produce:
- Pre-enforcement evidence snapshot
- Post-enforcement evidence snapshot
- Enforcement adapter log
- POA&M update
- OSCAL SAR update

This audit trail is immutable, provenance-backed, and auditor-accessible.

---

## Summary

The UIAO Security Architecture Layer establishes:

1. **Threat Model** — 6 adversary profiles, 8 attack surfaces, 7 threat mitigations
2. **Trust Boundaries** — Plane, service, tenant, and plugin trust boundaries
3. **Identity & Access Model** — 4 identity types with least-privilege scoping
4. **Key Management** — 4 key classes, rotation schedules, HSM-backing for FedRAMP
5. **Data Protection** — Encryption at rest and in transit, memory safety
6. **Plugin Sandboxing** — Containerized execution, schema enforcement, capability scoping
7. **Enforcement Safety** — Authorization, rollback, and immutable audit trail

This is the layer that makes UIAO **trustworthy**, **assessable**, and **FedRAMP-ready**.
