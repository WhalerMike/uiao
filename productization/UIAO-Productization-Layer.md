# UIAO Productization Layer

This layer defines how UIAO is packaged, priced, and deployed as a commercial product. It contains five major components.

---

## 1. Product Line Architecture (SKUs & Tiers)

### UIAO Standard
- SCuBA pipeline
- Evidence normalization
- KSI evaluation
- Basic OSCAL outputs (SSP, SAR)
- Single-tenant only

### UIAO Professional
- Everything in Standard
- Enforcement adapters
- Zero-trust integration
- Multi-tenant support
- Plugin marketplace access

### UIAO Enterprise
- Everything in Professional
- FedRAMP Moderate control pack
- ATO package generator
- Auditor delegation
- Compliance data lake retention policies
- SLA-backed support

---

## 2. UIAO for M365 FedRAMP Moderate (Flagship Offering)

The flagship UIAO product for federal agencies and contractors operating M365 in FedRAMP Moderate environments.

### Included Control Pack
- SCuBA → NIST 800-53 → FedRAMP Moderate mappings
- 10 KSI rules (MFA, legacy auth, admin count, sharing, DLP, etc.)
- OSCAL SSP/SAP/SAR/POA&M emitters
- Conditional Access enforcement adapter

### Target Buyers
- Federal agency IT and security teams
- FedRAMP-authorized M365 contractors
- Cloud service offerings (CSOs) with M365

### Differentiators
- Only OSCAL-native M365 compliance automation
- Drift-to-POA&M automation
- Full provenance chain
- Auditor-ready API

---

## 3. UIAO for Zero-Trust Identity (Identity-Only SKU)

Focused product for organizations wanting to prove zero-trust identity posture.

### Supported Controls
- IA-2 (MFA)
- AC-17 (Remote Access / Legacy Auth)
- AC-2(1) (Admin Count)
- Conditional Access policy coverage

### Evidence Sources
- Azure AD
- Conditional Access
- Sign-in risk / user risk signals

### Outputs
- Identity posture dashboard
- Identity drift detection
- Identity-only OSCAL SSP/SAR

---

## 4. UIAO for SaaS Security Posture (SSPM-style SKU)

Deterministic and OSCAL-native SaaS security posture management — a direct alternative to SSPM vendors.

### Supported SaaS (via plugins)
- Microsoft 365
- Google Workspace (future)
- Salesforce (future)
- Okta (future)

### Evidence Sources
- Sharing settings
- Audit logs

### Control Pack
- CIS SaaS Benchmarks
- Zero-Trust SaaS controls
- Custom enterprise controls

### Outputs
- SaaS posture dashboard
- SaaS drift detection
- SaaS evidence bundles
- SaaS OSCAL profile

---

## 5. UIAO Deployment Models (Commercial, GCC, GCC-M)

### Commercial
- Standard cloud deployment
- Multi-tenant capable
- Plugin marketplace fully available
- Standard SLA

### GCC (Government Community Cloud)
- US-only data residency
- ITAR-aware configuration
- FedRAMP-ready
- Restricted plugin marketplace (first-party only)

### GCC-M (GCC High / DoD)
- DoD IL4/IL5 compliant deployment
- No cross-tenant data
- Air-gap compatible
- FedRAMP High control pack
- DoD-specific OSCAL profiles

---

## What This Layer Unlocks

With the Productization Layer, UIAO becomes:
- **Sellable** — defined SKUs with clear value propositions
- **Deployable** — multiple models for commercial and government
- **Differentiable** — uniquely positioned against SSPM vendors and manual compliance tools
- **Investable** — crisp product narrative for investors and buyers

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
