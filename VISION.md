# UIAO Vision & Mission Scope

> **Classification:** CUI/FOUO
> **Canonical source:** This file is the authoritative mission statement for `uiao-core`.
> It is referenced by the README, the uiao-docs canon, and the UIAO Codex.

---

## What UIAO Is Designed to Accomplish

UIAO (Unified Identity-Addressing-Overlay Architecture) is a federal network
modernization platform purpose-built to eliminate the manual, error-prone, and
perpetually out-of-date compliance machinery that governs civilian agency
infrastructure today.

It replaces spreadsheets, point-in-time audits, and siloed vendor outputs with a
single deterministic engine: one strict YAML Single Source of Truth (SSOT) that
continuously generates every required artifact, enforces every required control,
and contains drift — automatically, repeatably, and in under 120 seconds.

---

## The Seven Pillars

### 1. Deterministic FedRAMP Moderate Rev 5 Automation
Full 247-control baseline (163 base + 84 enhancements) encoded in machine-readable
YAML. The engine generates OSCAL-native SSPs, POA&Ms, and profiles on demand.
No manual copy-paste. No stale artifacts. Authorization packages are a pipeline
output, not a document project.

### 2. CISA SCuBA / BOD 25-01 Two-Way Governance Envelope
UIAO implements SCuBA (Secure Cloud Business Applications) baselines as a live,
bidirectional governance loop — not a one-time checklist. Policy drift against
M365, Azure AD/Entra, and other covered platforms is detected, attributed, and
surfaced as structured evidence within the same OSCAL artifact stream that feeds
FedRAMP. BOD 25-01 mandatory timelines are tracked and enforced through the same
KSI compliance engine.

### 3. KSI Compliance Engine
163 Key Security Indicators across 7 categories provide continuous, quantitative
compliance health. Each KSI maps directly to NIST 800-53 controls, FedRAMP
parameters, and SCuBA policy items. The engine evaluates KSI state on every
pipeline run and embeds results in OSCAL back-matter as cryptographically linked
evidence — producing an auditable, immutable record of posture over time.

### 4. Immutable Evidence Fabric
Every compliance claim is backed by a tamper-evident evidence bundle: raw
collector output, normalized overlay, KSI evaluation result, and GPG-signed
commit hash. Evidence is linked into OSCAL back-matter and cannot be altered
without invalidating the chain. Auditors and authorizing officials get a
verifiable, timestamped record — not a screenshot in a folder.

### 5. Drift Detection & Containment in < 120 Seconds
Continuous validation runs against the YAML SSOT on every commit and on a
scheduled cadence. Drift — any deviation of live system state from the canon —
is detected, classified, and raised as a structured finding in under 120 seconds.
The architecture enforces the principle that drift is never silently tolerated:
it is always measured, always attributed, and always actionable.

### 6. Zero Trust / TIC 3.0 Modernization
UIAO's six control planes (Identity, Addressing, Overlay, Telemetry, Management,
Governance) directly implement Zero Trust Architecture (NIST SP 800-207) and
TIC 3.0 use cases. Identity is the root namespace: every IP address, certificate,
subnet, policy, and telemetry event is derived from and traceable back to an
authenticated identity claim. This makes Zero Trust an architectural property of
the system, not a compliance checkbox.

### 7. Future-Proof Governance Platform
UIAO is not built for a single directive. The adapter framework, KSI schema, and
evidence pipeline are intentionally generic. When a new CISA directive, OMB memo,
or cloud platform emerges, compliance coverage is added by extending the YAML
SSOT and the KSI rule set — without touching the generation engine. The platform
scales forward.

---

## What UIAO Replaces

| Legacy Practice | UIAO Replacement |
|---|---|
| Manual SSP authoring in Word/Excel | Deterministic OSCAL generation from YAML SSOT |
| Point-in-time FedRAMP audits | Continuous KSI evaluation + immutable Evidence Fabric |
| Separate SCuBA assessment process | Unified SCuBA/FedRAMP governance envelope in one pipeline |
| Vendor-specific compliance exports | Normalized adapter overlays feeding a single artifact stream |
| Spreadsheet-tracked POA&Ms | Machine-generated, OSCAL-native POA&M with evidence links |
| Passive telemetry dashboards | Telemetry as a real-time control input to drift detection |
| One-off BOD compliance reviews | BOD 25-01 timelines enforced as KSI rules with automated evidence |

---

## Alignment to Federal Mandates

| Mandate | UIAO Coverage |
|---|---|
| FedRAMP Moderate Rev 5 | Full 247-control baseline, OSCAL-native artifacts, continuous ATO evidence |
| CISA SCuBA Baselines | Live policy enforcement, bidirectional drift detection, structured findings |
| BOD 25-01 | Mandatory timeline tracking via KSI engine, evidence-backed closure |
| NIST SP 800-53 Rev 5 | Control library SSOT, parameter coverage, implementation statements |
| NIST SP 800-207 (Zero Trust) | Identity-as-root-namespace, six control planes, mTLS-anchored overlay |
| TIC 3.0 | Use-case alignment across all six control planes |
| NIST SP 800-63 | Identity assurance levels encoded in the addressing and overlay layers |
| FedRAMP 20x (emerging) | Architecture and schema designed for forward compatibility |
| CycloneDX SBOM | Generated per pipeline run, linked to OSCAL component inventory |

---

## The Eight Core Concepts

These are the architectural invariants that every component in UIAO must respect:

1. **Single Source of Truth (SSOT)** — Every claim has one authoritative origin. All other representations are derived pointers, never copies.
2. **Conversation as the atomic unit** — Every network interaction binds identity, certificates, addressing, path, QoS, and telemetry into one auditable unit.
3. **Identity as the root namespace** — Every IP, certificate, subnet, policy, and telemetry event derives from and is traceable to an authenticated identity.
4. **Deterministic addressing** — Network addressing is identity-derived and policy-driven, not administratively assigned.
5. **Certificate-anchored overlay** — mTLS anchors all tunnels, services, and trust relationships. Trust is cryptographic, not topological.
6. **Telemetry as control** — Telemetry is a real-time control input to drift detection and governance, not a passive reporting side-channel.
7. **Embedded governance and automation** — Governance is not a review process. It is executed through orchestrated, auditable, machine-driven workflows.
8. **Public service first** — Citizen experience, accessibility, and privacy are top-level architectural constraints, not post-hoc additions.

---

## Scope of the Canon

The full UIAO architecture is specified across a 20-document modernization canon
maintained in [uiao-docs](https://github.com/WhalerMike/uiao-docs) and rendered
at [whalermike.github.io/uiao-docs](https://whalermike.github.io/uiao-docs).

`uiao-core` is the execution engine for everything described in this document.

---

*Last updated: see git log. This file is part of the UIAO SSOT.*
