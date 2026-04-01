# UIAO-Core — MVP Roadmap  
**Version 1.0 — 6‑Week Delivery Plan**

This document defines the Minimum Viable Product (MVP) roadmap for the UIAO-Core Evidence + KSI Validation Pipeline. It includes scope, milestones, success criteria, dependencies, and risks.

---

# 1. MVP Scope

The MVP delivers a complete, end‑to‑end **continuous evidence + validation pipeline** covering:

### **Controls**
12–20 high‑impact NIST 800‑53 Rev 5 controls across:

- **AC** — Access Control  
- **IA** — Identification & Authentication  
- **AU** — Audit & Accountability  
- **SC** — System & Communications Protection  

### **Collectors**
- **Entra ID Collector** (sign‑ins, MFA, CA policies)  
- **Cisco SD‑WAN Collector** (policy compliance, tunnel health)  
- **InfoBlox Collector** (DNS/IPAM correctness)

### **Core Engine**
- **KSI Validator Engine** (rule loading, evidence evaluation, drift detection)
- **Evidence Bundle Exporter** (OSCAL + JSON + Quarto fragments)

### **Dashboard**
- **Quarto ATO Dashboard Profile**  
- Control coverage map  
- KSI pass/fail matrix  
- Drift indicators  
- Evidence freshness timers  

### **Reference Deployment**
A minimal “ATO in a Box” example deployment demonstrating:

- Identity-derived addressing  
- SD‑WAN segmentation  
- DNS/IPAM correctness  
- Automated evidence generation  
- Quarto dashboard rendering  

---

# 2. Six‑Week Implementation Plan

## **Week 1 — Foundations**
### Deliverables
- Final **KSI Schema** (`ksi.schema.json`)
- **Base Collector** class + registry
- **Validator Engine Skeleton**
- Directory structure for rules, collectors, validators, schemas

### Success Criteria
- Schema validates via JSON Schema tooling  
- BaseCollector supports provenance, hashing, timestamps  
- Validator loads rule YAML and enumerates KSIs  
- CI pipeline runs lint + type checks  

---

## **Week 2 — Identity Layer**
### Deliverables
- **Entra Collector** (sign‑ins, MFA, CA)
- **5 AC‑family KSI rules** (AC‑2, AC‑3, AC‑5, AC‑6, AC‑7)
- Rule DSL v0.1 (conditions, all_of/any_of)

### Success Criteria
- Entra collector returns canonical EvidenceObject  
- KSI rules load and evaluate in validator  
- At least one AC KSI passes end‑to‑end  

---

## **Week 3 — Network + DNS Layer**
### Deliverables
- **SD‑WAN Collector** (policy + tunnel health)
- **InfoBlox Collector** (DNS/IPAM correctness)
- **IA + SC KSI rules** (privileged access, encryption, segmentation)

### Success Criteria
- All three collectors operational  
- At least 10 KSIs fully executable  
- Drift detection stub implemented  

---

## **Week 4 — Evidence Layer**
### Deliverables
- **Evidence Bundle Schema** (`evidence-bundle.schema.json`)
- **OSCAL Observation Exporter**
- **JSON Summary Exporter**
- **Quarto Fragment Generator**

### Success Criteria
- Evidence bundle validates against schema  
- OSCAL observations load in OSCAL tooling  
- Quarto fragments render without errors  

---

## **Week 5 — Dashboard + Drift**
### Deliverables
- **Quarto Dashboard Profile** (`dashboard/_quarto.yml`)
- **Dashboard index.qmd** (coverage map, matrix, drift, freshness)
- Drift detection v1 (hash comparison, policy deltas)

### Success Criteria
- Dashboard renders from evidence bundle  
- Drift indicators appear for modified evidence  
- Coverage percentage auto‑calculates  

---

## **Week 6 — Reference Deployment**
### Deliverables
- **ATO in a Box** reference deployment  
- Bicep/Terraform templates  
- Example workload (simple web app behind overlay)  
- Documentation + testing

### Success Criteria
- One‑command deployment  
- Evidence bundle generated from live environment  
- Dashboard renders real data  
- Documentation complete and reproducible  

---

# 3. Success Criteria (Global)

- 12–20 KSIs fully validated end‑to‑end  
- Evidence bundle schema stable  
- Dashboard renders without manual edits  
- Reference deployment reproducible in < 60 minutes  
- All code type‑checked, linted, and tested  

---

# 4. Dependencies & Prerequisites

### Technical
- Azure subscription with Entra ID + Activity Logs  
- Cisco SD‑WAN vManage API access  
- InfoBlox WAPI access  
- Python 3.10+  
- Quarto CLI  
- OSCAL tooling (optional but recommended)

### Organizational
- Access to sample logs or test tenants  
- Agreement on KSI naming conventions  
- Agreement on rule DSL v0.1  

---

# 5. Risk Register

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| API rate limits / throttling | Medium | Medium | Caching, backoff, sampling |
| Incomplete test data | High | Medium | Provide synthetic fixtures |
| Rule DSL complexity | Medium | Low | Start minimal, extend later |
| Drift detection false positives | Medium | Medium | Add tuning + thresholds |
| Dashboard performance | Low | Low | Pre‑aggregate evidence |
| Collector authentication failures | High | Medium | Health checks + retries |

---

# 6. Summary

This MVP roadmap delivers a **complete, operational, continuous ATO pipeline** in six weeks, transforming UIAO-Core from a static canon into a **self‑verifying compliance engine**.

