# UIAO System Overview

## 1. Purpose and Positioning

UIAO is a deterministic compliance automation platform that:
- Normalizes policy and configuration data (e.g., SCuBA) into a stable Information Representation (IR)
- Evaluates that IR against KSI rules and NIST/FedRAMP controls
- Produces OSCAL-native SSP/SAP/SAR/POA&M
- Binds evidence → controls → enforcement → drift → remediation
- Exposes auditor-ready, read-only interfaces and operator-grade automation surfaces

It is not "just a scanner" or "just a documentation generator" — it is a control plane for compliance.

---

## 2. High-Level Architecture

**Core components:**
- UIAO Automation Server
  - API layer (REST)
  - Job orchestrator
  - Execution engine (SCuBA, KSI, OSCAL, enforcement)
  - Evidence collector framework
  - Drift engine
  - Enforcement runtime
  - Git integration
  - Audit & logging
- Data & models
  - IR object model
  - Evidence graph
  - Compliance data lake
  - OSCAL catalog/profile
  - EPL (Enforcement Policy Language)
  - CQL (Compliance Query Language)
- Surfaces
  - uiao-core (machine artifacts, scripts, rules, OSCAL emitters)
  - uiao-docs (human-facing reports, governance, ATO package)
  - Compliance CLI
  - Auditor API
  - Internal UI / dashboard

---

## 3. Data Flow: From Telemetry to ATO Outputs

1. **Telemetry ingestion** — SCuBA, Azure AD, M365, Defender, etc. → Raw Zone of data lake
2. **Normalization** — Evidence collectors convert raw data → UIAO IR → Normalized Zone
3. **Evaluation** — KSI engine evaluates IR → NIST/FedRAMP control mappings → findings
4. **Drift detection** — Drift engine compares snapshots → findings → POA&M entries
5. **Enforcement** — EPL policies evaluated → enforcement adapters invoked → evidence collected
6. **OSCAL generation** — SSP/SAP/SAR/POA&M emitters produce OSCAL JSON with evidence + provenance
7. **Publication** — Machine artifacts → uiao-core; Human artifacts → uiao-docs (GitHub Pages)

---

## 4. Governance and Multi-Tenant Model

- **uiao-core** = machine-facing, privileged, non-public
- **uiao-docs** = human-facing, public, consumer of machine output
- Per-tenant partitions in data lake and evidence graph
- Tenant-scoped identity and Auditor API access
- Shared responsibility: CSP (Microsoft) handles platform; UIAO handles evidence/evaluation; Customer handles policy/remediation

---

## 5. Interfaces and Personas

- **Operators / Maintainers** — Automation Server API, Compliance CLI, internal UI
- **Auditors / AOs** — Auditor API, uiao-docs, OSCAL SSP/SAP/SAR/POA&M
- **Engineers / Integrators** — Extend evidence collectors, enforcement adapters, EPL policies

---

## 6. What UIAO Is, in One Sentence

> UIAO is a deterministic, evidence-centric control plane that ingests SCuBA and other telemetry, maps it to NIST/FedRAMP controls, enforces policy where allowed, and emits OSCAL-native ATO artifacts with full provenance and drift-to-POA&M linkage.
